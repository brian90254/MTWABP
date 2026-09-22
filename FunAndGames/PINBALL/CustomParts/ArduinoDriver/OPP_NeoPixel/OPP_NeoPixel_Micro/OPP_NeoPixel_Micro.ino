/* Arduino Micro (ATmega32U4) as a USB serial OPP NeoPixel controller for MPF.
   Set LED_PIN and PIXEL_COUNT to match the strip. One OPP Gen2 card (0x20).
   MPF LED 0 maps to NeoPixel 0; each LED occupies R, G, B OPP channels.
   Requires the Adafruit NeoPixel library and an external 5 V LED supply.
*/
#include <Adafruit_NeoPixel.h>

const uint8_t LED_PIN = 6;
const uint16_t PIXEL_COUNT = 16; // Keep modest on the Micro; see RAM and show() note below.
const uint32_t OPP_SERIAL_NUMBER = 0x4D49434FUL; // "MICO"; change for additional units.
const uint8_t BOARD = 0x20;
const uint8_t EOM = 0xFF;
const uint16_t CHANNEL_COUNT = PIXEL_COUNT * 3;
const uint16_t MAX_BATCH_CHANNELS = 128; // MPF batches at most 128 channels.
const uint16_t MAX_FRAME = 8 + MAX_BATCH_CHANNELS + 1; // header + data + CRC
const uint8_t FADE_TICK_MS = 20;

static_assert(PIXEL_COUNT > 0 && CHANNEL_COUNT <= 4096,
              "OPP LED channels must fit the 12-bit NeoPixel range");

Adafruit_NeoPixel strip(PIXEL_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// A fade is held per channel, allowing MPF to update different LEDs independently.
uint8_t currentValue[CHANNEL_COUNT];
uint8_t startValue[CHANNEL_COUNT];
uint8_t targetValue[CHANNEL_COUNT];
uint32_t fadeStarted[CHANNEL_COUNT];
uint16_t fadeDuration[CHANNEL_COUNT];
uint8_t frame[MAX_FRAME];
uint16_t frameLength = 0;
uint16_t frameExpected = 0;
uint32_t lastByteAt = 0;
uint32_t lastShowAt = 0;
bool dirty = false;

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

uint8_t interpolated(uint16_t index, uint32_t now) {
  uint16_t duration = fadeDuration[index];
  if (duration == 0) return targetValue[index];
  uint32_t elapsed = now - fadeStarted[index];
  if (elapsed >= duration) {
    fadeDuration[index] = 0;
    return targetValue[index];
  }
  int16_t delta = (int16_t)targetValue[index] - startValue[index];
  return (uint8_t)(startValue[index] + (int32_t)delta * elapsed / duration);
}

void applyLedFrame() {
  if (crc8(frame, frameExpected - 1) != frame[frameExpected - 1]) return;
  uint16_t first = ((uint16_t)frame[2] << 8) | frame[3];
  uint16_t count = ((uint16_t)frame[4] << 8) | frame[5];
  uint16_t duration = ((uint16_t)frame[6] << 8) | frame[7];
  if (count == 0 || count > MAX_BATCH_CHANNELS ||
      first >= CHANNEL_COUNT || count > CHANNEL_COUNT - first) return;

  uint32_t now = millis();
  for (uint16_t i = 0; i < count; ++i) {
    uint16_t channel = first + i;
    uint8_t value = frame[8 + i];
    // A new fade starts from the current interpolated value, not the previous target.
    uint8_t from = interpolated(channel, now);
    currentValue[channel] = from;
    startValue[channel] = from;
    targetValue[channel] = value;
    fadeStarted[channel] = now;
    fadeDuration[channel] = duration;
    dirty = true;
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
    case 0x0D: { // NeoPixel wing. MPF also polls its advertised input pins.
      uint8_t response[7] = {BOARD, 0x0D, 0x06, 0, 0, 0, 0};
      response[6] = crc8(response, 6);
      Serial.write(response, sizeof(response));
      break;
    }
    case 0x08: reply(0x08, 0xFFFFFFFFUL); break; // All inputs inactive.
    default: break; // e.g. 0x13: turn off unused incandescent outputs.
  }
}

void readOpp() {
  // A damaged or truncated frame cannot block later requests indefinitely.
  if (frameLength && (uint32_t)(millis() - lastByteAt) > 50) {
    frameLength = frameExpected = 0;
  }
  while (Serial.available()) {
    uint8_t byte = (uint8_t)Serial.read();
    lastByteAt = millis();
    if (!frameLength) {
      if (byte == EOM) { Serial.write(EOM); continue; }
      if (byte == 0xF0) {
        const uint8_t inventory[] = {0xF0, BOARD};
        Serial.write(inventory, sizeof(inventory));
        continue; // Request EOM will complete the inventory response.
      }
      if (byte != BOARD) continue;
    }
    frame[frameLength++] = byte;
    if (frameLength == 2) {
      if (frame[1] == 0x40) frameExpected = 0; // Read count at bytes 4 and 5.
      else if (frame[1] == 0x13) frameExpected = 8;
      else frameExpected = 7;
    }
    if (frameLength == 6 && frame[1] == 0x40) {
      uint16_t count = ((uint16_t)frame[4] << 8) | frame[5];
      if (!count || count > MAX_BATCH_CHANNELS) {
        frameLength = frameExpected = 0;
        continue;
      }
      frameExpected = 9 + count;
    }
    if (frameExpected && frameLength == frameExpected) {
      processFrame();
      frameLength = frameExpected = 0;
    }
  }
}

void updatePixels() {
  uint32_t now = millis();
  if ((uint32_t)(now - lastShowAt) < FADE_TICK_MS) return;
  lastShowAt = now;
  bool changed = dirty;
  dirty = false;
  for (uint16_t channel = 0; channel < CHANNEL_COUNT; ++channel) {
    uint8_t value = interpolated(channel, now);
    if (value != currentValue[channel]) changed = true;
    currentValue[channel] = value;
  }
  if (!changed) return;
  for (uint16_t pixel = 0; pixel < PIXEL_COUNT; ++pixel) {
    uint16_t channel = pixel * 3;
    strip.setPixelColor(pixel, currentValue[channel], currentValue[channel + 1],
                        currentValue[channel + 2]);
  }
  strip.show(); // May interrupt USB reception briefly for long LED strips.
}

void setup() {
  strip.begin();
  strip.clear();
  strip.show();
  Serial.begin(115200);
  // Arduino Micro has native USB. Do not wait for Serial: MPF can connect later.
  // A startup EOM also releases MPF if the first sync byte was lost at reset.
  delay(50);
  Serial.write(EOM);
}

void loop() {
  readOpp();
  updatePixels();
}
