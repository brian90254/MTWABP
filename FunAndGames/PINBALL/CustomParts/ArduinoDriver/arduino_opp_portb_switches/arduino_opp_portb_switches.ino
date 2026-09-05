/*
  Arduino PORTB -> Mission Pinball Framework OPP switch bridge

  Implements the minimum OPP Gen2 protocol needed for one 8-input card.
  MPF discovers one input wing at OPP address 0x20 (card 0), then polls it.

  Electrical convention:
    - Every PORTB pin is configured INPUT_PULLUP.
    - Connect a switch between the PORTB pin and GND.
    - Open = logic 1 = inactive; closed = logic 0 = active in MPF.

  Board warning:
    - ATmega328P Uno/Nano: PB0..PB5 are Arduino D8..D13. PB6/PB7 are normally
      used by the crystal, so only MPF switch numbers 0..5 are usable.
    - ATmega2560 Mega: all eight PORTB bits are available, but their Arduino
      pin numbers are board-specific. Consult the Mega pinout.
    - This sketch intentionally targets classic AVR Arduino boards that expose
      DDRB, PORTB, and PINB. It is not portable to every Arduino architecture.
*/

#include <Arduino.h>

namespace Opp {
constexpr uint8_t kAddress = 0x20;       // First OPP Gen2 card; MPF card 0
constexpr uint8_t kGetSerial = 0x00;
constexpr uint8_t kGetVersion = 0x02;
constexpr uint8_t kReadInputs = 0x08;
constexpr uint8_t kGetGen2Config = 0x0D;
constexpr uint8_t kInputWing = 0x02;
constexpr uint8_t kInventory = 0xF0;
constexpr uint8_t kEndOfMessage = 0xFF;

constexpr uint32_t kSerialNumber = 0x41524442UL; // "ARDB"
constexpr uint8_t kVersionMajor = 2;
constexpr uint8_t kVersionMinor = 1;
constexpr uint8_t kVersionRevision = 0;
constexpr uint8_t kVersionBuild = 0;
}  // namespace Opp

constexpr unsigned long kBaudRate = 115200;

uint8_t packet[7];
uint8_t packetLength = 0;
bool commandSeenSinceEom = false;

// OPP uses CRC-8, polynomial 0x07, initial value 0xFF, no final XOR.
uint8_t crc8(const uint8_t *data, uint8_t length) {
  uint8_t crc = 0xFF;
  while (length--) {
    crc ^= *data++;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0x07)
                         : static_cast<uint8_t>(crc << 1);
    }
  }
  return crc;
}

void writePacket(uint8_t command, uint32_t value) {
  uint8_t response[7] = {
      Opp::kAddress,
      command,
      static_cast<uint8_t>(value >> 24),
      static_cast<uint8_t>(value >> 16),
      static_cast<uint8_t>(value >> 8),
      static_cast<uint8_t>(value),
      0,
  };
  response[6] = crc8(response, 6);
  Serial.write(response, sizeof(response));
  Serial.write(Opp::kEndOfMessage);
}

void sendInventory() {
  const uint8_t response[] = {
      Opp::kInventory, Opp::kAddress, Opp::kEndOfMessage};
  Serial.write(response, sizeof(response));
}

void sendSerialNumber() {
  writePacket(Opp::kGetSerial, Opp::kSerialNumber);
}

void sendVersion() {
  const uint32_t version =
      (static_cast<uint32_t>(Opp::kVersionMajor) << 24) |
      (static_cast<uint32_t>(Opp::kVersionMinor) << 16) |
      (static_cast<uint32_t>(Opp::kVersionRevision) << 8) |
      Opp::kVersionBuild;
  writePacket(Opp::kGetVersion, version);
}

void sendGen2Config() {
  // Four OPP "wing" descriptors. Wing 0 is an 8-input board; the rest empty.
  uint8_t response[7] = {
      Opp::kAddress,
      Opp::kGetGen2Config,
      Opp::kInputWing,
      0x00,
      0x00,
      0x00,
      0,
  };
  response[6] = crc8(response, 6);
  Serial.write(response, sizeof(response));
  Serial.write(Opp::kEndOfMessage);
}

void sendInputs() {
  // OPP input bits are active-low. Setting unimplemented upper bits high keeps
  // them inactive; the eight PORTB bits occupy OPP switch numbers 0..7.
  const uint32_t state = 0xFFFFFF00UL | static_cast<uint32_t>(PINB);
  writePacket(Opp::kReadInputs, state);
}

void processPacket(const uint8_t *request) {
  if (request[0] != Opp::kAddress || crc8(request, 6) != request[6]) {
    return;
  }

  switch (request[1]) {
    case Opp::kGetSerial:
      sendSerialNumber();
      break;
    case Opp::kGetVersion:
      sendVersion();
      break;
    case Opp::kReadInputs:
      sendInputs();
      break;
    case Opp::kGetGen2Config:
      sendGen2Config();
      break;
    default:
      break;  // This bridge intentionally exposes switches only.
  }
}

void consumeByte(uint8_t incoming) {
  if (packetLength == 0) {
    if (incoming == Opp::kEndOfMessage) {
      // MPF sends standalone 0xFF bytes while synchronizing. Do not add a
      // second reply after the terminator belonging to a command batch.
      if (!commandSeenSinceEom) {
        Serial.write(Opp::kEndOfMessage);
      }
      commandSeenSinceEom = false;
      return;
    }

    if (incoming == Opp::kInventory) {
      sendInventory();
      commandSeenSinceEom = true;
      return;
    }

    if (incoming != Opp::kAddress) {
      return;
    }
  }

  packet[packetLength++] = incoming;
  if (packetLength == sizeof(packet)) {
    processPacket(packet);
    packetLength = 0;
    commandSeenSinceEom = true;
  }
}

void setup() {
  // All PORTB pins input, with internal pull-ups enabled.
  DDRB = 0x00;
  PORTB = 0xFF;

  Serial.begin(kBaudRate);
}

void loop() {
  while (Serial.available() > 0) {
    consumeByte(static_cast<uint8_t>(Serial.read()));
  }
}

