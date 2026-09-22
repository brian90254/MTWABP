/*
  Arduino Micro: 8 independent WS2812/NeoPixel chains x 64 LEDs = 512 RGB LEDs.
  MPF sees one OPP Gen2 card at 0x20 with a NeoPixel wing.

  OPP LED numbers 0..511 map as follows:
    0..63: pin D2, 64..127: D3, ..., 448..511: D9.
  Each LED uses three OPP channels in R,G,B order. The Adafruit library
  converts RGB to the strip's physical GRB order (change NEO_GRB if needed).

  SRAM is tight on the ATmega32U4: this version stores one 1536-byte RGB image,
  one reusable 192-byte strip buffer, and a 137-byte MPF input frame.
  MPF fade durations are accepted but colors are applied immediately. For
  smooth simultaneous hardware fades across 512 LEDs, use a board with more
  RAM and a suitable LED output engine.
*/
#include <Adafruit_NeoPixel.h>

// MPF LED = (chain * 64) + pixel; change pins to match your wiring.
const uint8_t LED_PINS[8] = {2, 3, 4, 5, 6, 7, 8, 9};
const uint8_t LEDS_PER_CHAIN = 64;
const uint16_t CHANNEL_COUNT = 8U * LEDS_PER_CHAIN * 3U;
const uint8_t BOARD = 0x20;
const uint8_t EOM = 0xFF;
const uint32_t OPP_SERIAL_NUMBER = 0x4D49434FUL; // "MICO"
const uint16_t MAX_BATCH_CHANNELS = 128; // MPF batch limit.
const uint16_t MAX_FRAME = 9U + MAX_BATCH_CHANNELS;

static_assert(CHANNEL_COUNT <= 4096, "OPP NeoPixel channel range exceeded");

// Only one Adafruit pixel buffer is allocated; setPin() selects the chain.
Adafruit_NeoPixel strip(LEDS_PER_CHAIN, LED_PINS[0], NEO_GRB + NEO_KHZ800);
uint8_t rgb[CHANNEL_COUNT];
uint8_t frame[MAX_FRAME];
uint16_t frameLength = 0;
uint16_t frameExpected = 0;
uint32_t lastByteAt = 0;
uint8_t dirtyChains = 0;
uint8_t nextChain = 0;

uint8_t crc8(const uint8_t *bytes, uint16_t length) {
  uint8_t crc = 0xFF;
  while (length--) {
    crc ^= *bytes++;
    for (uint8_t bit = 0; bit < 8; ++bit)
      crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
  }
  return crc;
}

void reply(uint8_t command, uint32_t value) {
  uint8_t response[7] = {BOARD, command, (uint8_t)(value >> 24),
                         (uint8_t)(value >> 16), (uint8_t)(value >> 8),
                         (uint8_t)value, 0};
  response[6] = crc8(response, 6);
  Serial.write(response, sizeof(response));
  // The request's trailing EOM gets its own echo after this packet.
}

void applyLedFrame() {
  if (crc8(frame, frameExpected - 1) != frame[frameExpected - 1]) return;
  uint16_t first = ((uint16_t)frame[2] << 8) | frame[3];
  uint16_t count = ((uint16_t)frame[4] << 8) | frame[5];
  // frame[6..7] is MPF fade duration. See the SRAM note above.
  if (count == 0 || count > MAX_BATCH_CHANNELS ||
      first >= CHANNEL_COUNT || count > CHANNEL_COUNT - first) return;

  for (uint16_t i = 0; i < count; ++i) {
    uint16_t channel = first + i;
    uint8_t value = frame[8 + i];
    if (rgb[channel] != value) {
      rgb[channel] = value;
      dirtyChains |= (uint8_t)(1U << (channel / (LEDS_PER_CHAIN * 3U)));
    }
  }
}

void processFrame() {
  if (frame[0] != BOARD) return;
  if (frame[1] == 0x40) {
    applyLedFrame();
    return;
  }
  if (frameExpected != 7 || crc8(frame, 6) != frame[6]) return;
  switch (frame[1]) {
    case 0x00: reply(0x00, OPP_SERIAL_NUMBER); break;
    case 0x02: reply(0x02, 0x02010000UL); break;
    case 0x0D: {
      uint8_t response[7] = {BOARD, 0x0D, 0x06, 0, 0, 0, 0};
      response[6] = crc8(response, 6);
      Serial.write(response, sizeof(response));
      break;
    }
    case 0x08: reply(0x08, 0xFFFFFFFFUL); break; // Neo wing's inputs inactive.
    default: break; // MPF may send 0x13 to disable incandescent outputs.
  }
}

void readOpp() {
  if (frameLength && (uint32_t)(millis() - lastByteAt) > 50)
    frameLength = frameExpected = 0;

  while (Serial.available()) {
    uint8_t byte = (uint8_t)Serial.read();
    lastByteAt = millis();
    if (!frameLength) {
      if (byte == EOM) { Serial.write(EOM); continue; }
      if (byte == 0xF0) {
        const uint8_t inventory[] = {0xF0, BOARD};
        Serial.write(inventory, sizeof(inventory));
        continue;
      }
      if (byte != BOARD) continue;
    }
    frame[frameLength++] = byte;
    if (frameLength == 2) {
      if (frame[1] == 0x40) frameExpected = 0;
      else if (frame[1] == 0x13) frameExpected = 8;
      else frameExpected = 7;
    }
    if (frameLength == 6 && frame[1] == 0x40) {
      uint16_t count = ((uint16_t)frame[4] << 8) | frame[5];
      if (!count || count > MAX_BATCH_CHANNELS) {
        frameLength = frameExpected = 0;
        continue;
      }
      frameExpected = 9U + count;
    }
    if (frameExpected && frameLength == frameExpected) {
      processFrame();
      frameLength = frameExpected = 0;
    }
  }
}

void refreshOneChain() {
  if (!dirtyChains) return;
  for (uint8_t attempt = 0; attempt < 8; ++attempt) {
    uint8_t chain = (nextChain + attempt) & 7;
    uint8_t bit = (uint8_t)(1U << chain);
    if (!(dirtyChains & bit)) continue;
    nextChain = (chain + 1) & 7;
    dirtyChains &= (uint8_t)~bit;
    strip.setPin(LED_PINS[chain]);
    uint16_t base = (uint16_t)chain * LEDS_PER_CHAIN * 3U;
    for (uint8_t pixel = 0; pixel < LEDS_PER_CHAIN; ++pixel) {
      uint16_t index = base + (uint16_t)pixel * 3U;
      strip.setPixelColor(pixel, rgb[index], rgb[index + 1], rgb[index + 2]);
    }
    strip.show(); // About 2 ms per 64-pixel chain; USB timing needs real testing.
    return; // Service USB before updating another chain.
  }
}

void setup() {
  strip.begin();
  strip.clear();
  for (uint8_t chain = 0; chain < 8; ++chain) {
    strip.setPin(LED_PINS[chain]);
    strip.show();
  }
  Serial.begin(115200);
  delay(50);
  Serial.write(EOM); // Recover from MPF's first sync byte arriving during reset.
}

void loop() {
  readOpp();
  refreshOneChain();
}
