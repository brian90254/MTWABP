/*
  Arduino Mega 2560: 40 independently switched outputs for MPF OPP lamps.

  MPF sees two OPP Gen2 incandescent cards on one USB serial connection:
    OPP card 0, lamp 0..31 -> Arduino D22..D53
    OPP card 1, lamp 0..7  -> Arduino A8..A15 (digital outputs)

  These pins are logic outputs only. Provide external transistor drivers,
  flyback protection for inductive loads, and a suitable separate lamp supply.
  On reset and before MPF starts, every output is LOW. Nonzero MPF brightness
  sets an output HIGH; zero sets it LOW. Fade durations are ignored.
*/
#if !defined(__AVR_ATmega2560__)
#error "Select Arduino Mega or Mega 2560 in the Arduino IDE"
#endif

const uint8_t LAMP_PINS[40] = {
  22, 23, 24, 25, 26, 27, 28, 29,
  30, 31, 32, 33, 34, 35, 36, 37,
  38, 39, 40, 41, 42, 43, 44, 45,
  46, 47, 48, 49, 50, 51, 52, 53,
  A8, A9, A10, A11, A12, A13, A14, A15
};

const uint8_t CARD_0 = 0x20;
const uint8_t CARD_1 = 0x21;
const uint8_t EOM = 0xFF;
const uint16_t MAX_BATCH = 128; // MPF's maximum channels in one update.
const uint16_t MAX_FRAME = 9 + MAX_BATCH;
const uint32_t SERIAL_NUMBER = 0x4C414D50UL; // "LAMP", unique for this device.

uint8_t frame[MAX_FRAME];
uint16_t frameLength = 0;
uint16_t frameExpected = 0;
uint32_t lastByteAt = 0;

uint8_t crc8(const uint8_t *data, uint16_t length) {
  uint8_t crc = 0xFF;
  while (length--) {
    crc ^= *data++;
    for (uint8_t bit = 0; bit < 8; ++bit)
      crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
  }
  return crc;
}

void reply(uint8_t address, uint8_t command, uint32_t value) {
  uint8_t response[7] = {address, command, (uint8_t)(value >> 24),
                         (uint8_t)(value >> 16), (uint8_t)(value >> 8),
                         (uint8_t)value, 0};
  response[6] = crc8(response, 6);
  Serial.write(response, sizeof(response));
  // The request's trailing EOM will be echoed separately.
}

void sendConfig(uint8_t address) {
  // 0x03 means an eight-output incandescent wing. Four wings on card 0,
  // one wing on card 1. Remaining wing slots are empty (0x00).
  uint8_t response[7] = {address, 0x0D, 0x03,
                         (uint8_t)(address == CARD_0 ? 0x03 : 0x00),
                         (uint8_t)(address == CARD_0 ? 0x03 : 0x00),
                         (uint8_t)(address == CARD_0 ? 0x03 : 0x00), 0};
  response[6] = crc8(response, 6);
  Serial.write(response, sizeof(response));
}

void applyLampUpdate() {
  if (crc8(frame, frameExpected - 1) != frame[frameExpected - 1]) return;
  uint16_t first = ((uint16_t)frame[2] << 8) | frame[3];
  uint16_t count = ((uint16_t)frame[4] << 8) | frame[5];
  // frame[6..7] is fade duration. Physical outputs here are strictly on/off.
  uint8_t address = frame[0];
  uint8_t lampCount = address == CARD_0 ? 32 : 8;
  if (!count || count > MAX_BATCH || first < 0x1000 ||
      first >= 0x1000 + lampCount || count > 0x1000 + lampCount - first)
    return;

  uint8_t pinOffset = address == CARD_0 ? 0 : 32;
  for (uint16_t i = 0; i < count; ++i) {
    uint8_t pinIndex = pinOffset + (first - 0x1000) + i;
    digitalWrite(LAMP_PINS[pinIndex], frame[8 + i] ? HIGH : LOW);
  }
}

void processFrame() {
  uint8_t address = frame[0];
  if (address != CARD_0 && address != CARD_1) return;
  if (frame[1] == 0x40) { applyLampUpdate(); return; }
  if (frameExpected == 8 && frame[1] == 0x13) {
    // MPF sends 0x13/0x07 to make sure incandescent outputs are off at
    // startup. It is addressed to the first card in the chain.
    if (address == CARD_0 && crc8(frame, 7) == frame[7] && frame[2] == 0x07 &&
        frame[3] == 0 && frame[4] == 0 && frame[5] == 0 && frame[6] == 0) {
      for (uint8_t i = 0; i < 40; ++i) digitalWrite(LAMP_PINS[i], LOW);
    }
    return;
  }
  if (frameExpected != 7 || crc8(frame, 6) != frame[6]) return;
  switch (frame[1]) {
    case 0x00: reply(address, 0x00, SERIAL_NUMBER); break;
    case 0x02: reply(address, 0x02, 0x02010000UL); break;
    case 0x0D: sendConfig(address); break;
    default: break; // No input wings or coil functions on this controller.
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
        const uint8_t inventory[] = {0xF0, CARD_0, CARD_1};
        Serial.write(inventory, sizeof(inventory));
        continue;
      }
      if (byte != CARD_0 && byte != CARD_1) continue;
    }
    frame[frameLength++] = byte;
    if (frameLength == 2) {
      if (frame[1] == 0x40) frameExpected = 0; // Wait for the count field.
      else if (frame[1] == 0x13) frameExpected = 8;
      else frameExpected = 7;
    }
    if (frameLength == 6 && frame[1] == 0x40) {
      uint16_t count = ((uint16_t)frame[4] << 8) | frame[5];
      if (!count || count > MAX_BATCH) {
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

void setup() {
  // AVR outputs reset as inputs. Write LOW before changing their direction so
  // the output latch cannot momentarily request an active transistor.
  for (uint8_t i = 0; i < 40; ++i) {
    digitalWrite(LAMP_PINS[i], LOW);
    pinMode(LAMP_PINS[i], OUTPUT);
  }
  Serial.begin(115200);
  delay(50);
  Serial.write(EOM); // Startup sync for MPF if its first byte was lost.
}

void loop() {
  readOpp();
}
