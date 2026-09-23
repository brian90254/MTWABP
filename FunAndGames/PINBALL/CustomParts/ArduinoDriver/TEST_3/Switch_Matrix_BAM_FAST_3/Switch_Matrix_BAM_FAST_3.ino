
// --------------------------------------------
/*  
INSTRUCTIONS:

This code scans a 5x8 switch matrix, mirrors the 40 switch states to digital
outputs for FAST hardware, and presents the same switches to MPF as two OPP
Gen2 input cards over the Arduino USB serial port.


CODE FLOW:

  -  Set the first drive line output.
  -  Scan first input.
  -  A normally-open switch is active when the selected row drives its input HIGH.
  -  Make the switch states available to MPF through the OPP protocol.
  -  Loop through all eight inputs.
  -  Loop through all five drive lines.
  -  Delay.
  -  Repeat.
  
For questions or comments, check the blog:
http://howtobuildapinballmachine.wordpress.com

*/


//  --------------------------
//  BUILD VARIABLES HERE
#define DEBOUNCE_MODE 1
#define SERIAL_MONITOR 0 // Must remain 0 while MPF/OPP is using Serial.
#define OUTPUT_DIRECT 1
#define SWITCH_ACTIVE_LEVEL HIGH // Normally-open switch: closure reads HIGH.

//  --------------------------
//  VARIABLES
unsigned char j = 0;  //
unsigned char i = 0;  //
unsigned char k = 0;  //

unsigned char flagLoops = 0;  //

//  --------------------------
//  SWITCHES (OLD, was x40)
//unsigned char switchStateNow[40]; // start no digit selected
//unsigned char switchStatePrev[40];  // start no digit selected
//unsigned char switchNew[40];  //
//unsigned char switchDebounce[40];
//  --------------------------
//  SWITCHES (NEW, now x48)
unsigned char switchStateNow[48];  // start no digit selected
unsigned char switchStatePrev[48];  // start no digit selected
unsigned char switchNew[48];  //
unsigned char switchDebounce[48];


#define SWITCH_DEBOUNCE_DURATION 10 //10 loops


// *******************************
// LIGHTING SERIAL SETUP
// *******************************
#include <SoftwareSerial.h>

SoftwareSerial mySerialOne(19, 18); // RX, TX
SoftwareSerial mySerialTwo(17, 16); // RX, TX
SoftwareSerial mySerialThree(15, 14); // RX, TX


// *******************************
// MPF / OPP SERIAL INTERFACE
// *******************************
// The 40 matrix switches are exposed as:
//   OPP card 0, switches 0-31  = matrix switches 0-31
//   OPP card 1, switches 0-7   = matrix switches 32-39
//
// The physical matrix is active-high: an open switch reads LOW and a closed
// switch reads HIGH. OPP represents an active input with a cleared bit, so
// oppGetInputState() translates the active-high matrix state to active-low OPP.

#define OPP_BAUD_RATE       115200UL
#define OPP_CARD_0          0x20
#define OPP_CARD_1          0x21
#define OPP_GET_SERIAL      0x00
#define OPP_GET_VERSION     0x02
#define OPP_READ_INPUTS     0x08
#define OPP_GET_GEN2_CONFIG 0x0D
#define OPP_INPUT_WING      0x02
#define OPP_INVENTORY       0xF0
#define OPP_EOM             0xFF

// Report OPP firmware 2.1.0.0, which is new enough for current MPF.
#define OPP_VERSION_VALUE   0x02010000UL
#define OPP_SERIAL_NUMBER   0x42414D32UL  // ASCII "BAM2"

unsigned char oppRxPacket[7];
unsigned char oppRxLength = 0;


unsigned char oppCrc8(const unsigned char *data, unsigned char length)
{
  unsigned char crc = 0xFF;

  while (length--)
  {
    crc ^= *data++;
    for (unsigned char bit = 0; bit < 8; bit++)
    {
      if (crc & 0x80)
      {
        crc = (unsigned char)((crc << 1) ^ 0x07);
      }
      else
      {
        crc = (unsigned char)(crc << 1);
      }
    }
  }

  return crc;
}


void oppWritePacket(unsigned char address, unsigned char command,
                    unsigned long value)
{
  unsigned char response[7];

  response[0] = address;
  response[1] = command;
  response[2] = (unsigned char)(value >> 24);
  response[3] = (unsigned char)(value >> 16);
  response[4] = (unsigned char)(value >> 8);
  response[5] = (unsigned char)value;
  response[6] = oppCrc8(response, 6);

  // Do not write OPP_EOM here. MPF may send requests for both cards in one
  // batch. The EOM is echoed once after every response in that batch.
  Serial.write(response, sizeof(response));
}


unsigned long oppGetInputState(unsigned char address)
{
  unsigned long state = 0xFFFFFFFFUL;

  if (address == OPP_CARD_0)
  {
    // Card 0 contains matrix switch numbers 0 through 31.
    for (unsigned char switchNumber = 0; switchNumber < 32; switchNumber++)
    {
      if (switchStateNow[switchNumber] == SWITCH_ACTIVE_LEVEL)
      {
        state &= ~(1UL << switchNumber);
      }
    }
  }
  else if (address == OPP_CARD_1)
  {
    // Card 1 uses only its first eight inputs for matrix switches 32-39.
    for (unsigned char switchNumber = 0; switchNumber < 8; switchNumber++)
    {
      if (switchStateNow[switchNumber + 32] == SWITCH_ACTIVE_LEVEL)
      {
        state &= ~(1UL << switchNumber);
      }
    }
  }

  return state;
}


void oppSendGen2Config(unsigned char address)
{
  unsigned char response[7];

  response[0] = address;
  response[1] = OPP_GET_GEN2_CONFIG;

  if (address == OPP_CARD_0)
  {
    // Four eight-input wings = 32 inputs.
    response[2] = OPP_INPUT_WING;
    response[3] = OPP_INPUT_WING;
    response[4] = OPP_INPUT_WING;
    response[5] = OPP_INPUT_WING;
  }
  else
  {
    // One eight-input wing = 8 inputs.
    response[2] = OPP_INPUT_WING;
    response[3] = 0x00;
    response[4] = 0x00;
    response[5] = 0x00;
  }

  response[6] = oppCrc8(response, 6);
  Serial.write(response, sizeof(response));
}


void oppProcessPacket(const unsigned char *request)
{
  unsigned char address = request[0];

  if ((address != OPP_CARD_0 && address != OPP_CARD_1) ||
      oppCrc8(request, 6) != request[6])
  {
    return;
  }

  switch (request[1])
  {
    case OPP_GET_SERIAL:
      // MPF normally requests this from address 0x20 only.
      oppWritePacket(address, OPP_GET_SERIAL, OPP_SERIAL_NUMBER);
      break;

    case OPP_GET_VERSION:
      oppWritePacket(address, OPP_GET_VERSION, OPP_VERSION_VALUE);
      break;

    case OPP_READ_INPUTS:
      oppWritePacket(address, OPP_READ_INPUTS, oppGetInputState(address));
      break;

    case OPP_GET_GEN2_CONFIG:
      oppSendGen2Config(address);
      break;

    default:
      // This device intentionally implements input cards only.
      break;
  }
}


void oppConsumeByte(unsigned char incoming)
{
  if (oppRxLength == 0)
  {
    if (incoming == OPP_EOM)
    {
      // End the response batch. This also supplies the echo MPF expects while
      // initially synchronizing with an OPP processor.
      Serial.write((unsigned char)OPP_EOM);
      return;
    }

    if (incoming == OPP_INVENTORY)
    {
      // The trailing EOM is emitted when MPF's request EOM is consumed.
      Serial.write((unsigned char)OPP_INVENTORY);
      Serial.write((unsigned char)OPP_CARD_0);
      Serial.write((unsigned char)OPP_CARD_1);
      return;
    }

    if (incoming != OPP_CARD_0 && incoming != OPP_CARD_1)
    {
      return;
    }
  }

  oppRxPacket[oppRxLength++] = incoming;

  if (oppRxLength == sizeof(oppRxPacket))
  {
    oppProcessPacket(oppRxPacket);
    oppRxLength = 0;
  }
}


void serviceOppSerial()
{
  while (Serial.available() > 0)
  {
    oppConsumeByte((unsigned char)Serial.read());
  }
}


void setup() {  

// *******************************
// MPF / OPP SERIAL SETUP
// *******************************
  Serial.begin(OPP_BAUD_RATE);

// *******************************
// LIGHTING SERIAL SETUP
// *******************************
//  mySerialOne.begin(9600);
//  mySerialTwo.begin(9600);
//  mySerialThree.begin(9600);

//  mySerialOne.begin(38400);
//  mySerialTwo.begin(38400);
//  mySerialThree.begin(38400);
  
// *******************************
// MATRIX SETUP SECTION
// ******************************* 

// -----------------
// MATRIX DRIVE OUTPUT
  pinMode(A0,OUTPUT); // analog in used a row drive out
  pinMode(A1,OUTPUT); // analog in used a row drive out
  pinMode(A2,OUTPUT); // analog in used a row drive out
  pinMode(A3,OUTPUT); // analog in used a row drive out
  pinMode(A4,OUTPUT); // analog in used a row drive out
  pinMode(A5,OUTPUT); // analog in used a row drive out

// -----------------------
// MATRIX SWITCH INPUT
  pinMode(2,INPUT);
  pinMode(3,INPUT);
  pinMode(4,INPUT);
  pinMode(5,INPUT);
  pinMode(6,INPUT);
  pinMode(7,INPUT);
  pinMode(8,INPUT);
  pinMode(9,INPUT);

// -------------------
// DEBUG LED INDICATOR
  pinMode(10,OUTPUT); // analog in used a row drive out

// -------------------------
// FAST SWITCH OUTPUT
// TODO check these, should set almost all remaining pins to output
  //for (j = 22; j < 46; j++)
  for (j = 22; j < 54; j++) // Doesn't include last analog channels
  {
      pinMode(j,OUTPUT); // to FAST hardware
  }

// -----------------------
// LAST BANK OF FAST OUTPUTS
  pinMode(A8,OUTPUT);
  pinMode(A9,OUTPUT);
  pinMode(A10,OUTPUT);
  pinMode(A11,OUTPUT);
  pinMode(A12,OUTPUT);
  pinMode(A13,OUTPUT);
  pinMode(A14,OUTPUT);
  pinMode(A15,OUTPUT);

  
//  --------------------------
//  INITIALIZE SWITCH STATE INACTIVE; N.O. CLOSURES TRIGGER ON THE RISING EDGE
  //for (j = 0; j < 40; j++) // OLD, 40 outputs
  for (j = 0; j < 48; j++) // NEW, 48 outputs
  {
    switchStateNow[j] = LOW;
    switchStatePrev[j] = LOW;
    switchNew[j] = 0;
    switchDebounce[j] = 100;
  }

  delay(50);
  Serial.write((unsigned char)OPP_EOM);
  Serial.flush();
  
} // end setup


void loop() 
{

  // Service any OPP requests before scanning the matrix. At 115200 baud the
  // complete request is normally handled in one pass.
  serviceOppSerial();


// *******************************
// MATRIX SECTION
// ******************************* 
  flagLoops = !flagLoops;
  if (flagLoops == 0)
  {
  digitalWrite(10, HIGH); // DEBUG LED
  }
  else
  {
  digitalWrite(10, LOW); // DEBUG LED
  }
  
  //  *****************************************
  //  -----------------------------------------
  //             START READ SWITCH
  //  -----------------------------------------
  //  *****************************************  

// *******************************
// DRIVE SECTION
// ******************************* 
  // SET DRIVE LINES HERE
  for (j = 0; j < 5; j++) // 0 to 4
  {
    // START ALL LOW (no signal)
//    digitalWrite(14, LOW); // pins 14-17
//    digitalWrite(15, LOW); // pins 14-17
//    digitalWrite(16, LOW); // pins 14-17
//    digitalWrite(17, LOW); // pins 14-17    
//    digitalWrite(18, LOW); // pins 14-17 

    // START ALL LOW (no signal)
    digitalWrite(A0, LOW); // pins 14-17
    digitalWrite(A1, LOW); // pins 14-17
    digitalWrite(A2, LOW); // pins 14-17
    digitalWrite(A3, LOW); // pins 14-17    
    digitalWrite(A4, LOW); // pins 14-17
    digitalWrite(A5, LOW); // pins 14-17
    
    // DRIVE ONE LINE HIGH
    //digitalWrite((j+14), HIGH); // pins 14-17

    // DRIVE ONE LINE HIGH
    switch (j)
    {
      default:
      break;
      
      case 0:
      digitalWrite(A0, HIGH);
      break;

      case 1:
      digitalWrite(A1, HIGH);
      break;

      case 2:
      digitalWrite(A2, HIGH);
      break;

      case 3:
      digitalWrite(A3, HIGH);
      break;

      case 4:
      digitalWrite(A4, HIGH);
      break;

      // doesn't get here, only 0~4
      case 5:
      digitalWrite(A5, HIGH);
      break;     
    }
    
    // WAIT HERE FOR RISE TIME
    delayMicroseconds(400) ;


// *******************************
// SCANNING AND OUTPUT SECTION
// *******************************    
    // START SCAN
    for (i = 0; i < 8; i++) 
    { 
      switchStatePrev[((j*8) + i)] = switchStateNow[((j*8) + i)]; // rotate variable
      switchStateNow[((j*8) + i)] = digitalRead(i + 2); // pins 2-9

      #if (OUTPUT_DIRECT == 1)
        if (switchStateNow[(j*8) + i] == SWITCH_ACTIVE_LEVEL)
        {
          if (j == 4)
          {
            // DRIVE OUTPUT LINE HIGH
            switch (i)
            {
              default:
              break;
              
              case 0:
              digitalWrite(A8, HIGH);
              break;
        
              case 1:
              digitalWrite(A9, HIGH);
              break;
        
              case 2:
              digitalWrite(A10, HIGH);
              break;
        
              case 3:
              digitalWrite(A11, HIGH);
              break;
        
              case 4:
              digitalWrite(A12, HIGH);
              break;
        
              case 5:
              digitalWrite(A13, HIGH);
              break;

              case 6:
              digitalWrite(A14, HIGH);
              break;

              case 7:
              digitalWrite(A15, HIGH);
              break;
            }
          }
          else
          {
            digitalWrite((22 + (j*8) + i), HIGH);
          }
        }
        else
        {
          if (j == 4)
          {
            // DRIVE OUTPUT LINE HIGH
            switch (i)
            {
              default:
              break;
              
              case 0:
              digitalWrite(A8, LOW);
              break;
        
              case 1:
              digitalWrite(A9, LOW);
              break;
        
              case 2:
              digitalWrite(A10, LOW);
              break;
        
              case 3:
              digitalWrite(A11, LOW);
              break;
        
              case 4:
              digitalWrite(A12, LOW);
              break;
        
              case 5:
              digitalWrite(A13, LOW);
              break;

              case 6:
              digitalWrite(A14, LOW);
              break;

              case 7:
              digitalWrite(A15, LOW);
              break;
            }
          }
          else
          {
            digitalWrite((22 + (j*8) + i), LOW);
          }
        }
      #endif
          
      // check for a "new" state
    #if (DEBOUNCE_MODE)
      if ((switchStateNow[((j*8) + i)] == switchStatePrev[((j*8) + i)]) || (switchDebounce[((j*8) + i)] > 0))
    #else
      if ( switchStateNow[((j*8) + i)] == switchStatePrev[((j*8) + i)]) 
    #endif
      {
        switchNew[((j*8) + i)] = 0; // same as old
      } // end if
      
      else // must be new if not old and new equals one
      {
        if (switchStateNow[((j*8) + i)] == SWITCH_ACTIVE_LEVEL)
        {
          switchNew[((j*8) + i)] = 1; // new
          
          #if (DEBOUNCE_MODE)
            switchDebounce[((j*8) + i)] = SWITCH_DEBOUNCE_DURATION; // set timer
          #endif
          
          #if (SERIAL_MONITOR == 1)
            Serial.print("Switch = ");
            Serial.print((j*8) + i + 33); // TODO check this formatting later
            Serial.print("\r\n");
          #endif
          
        }
      } // end else
    } // end for i
  } // end for j    

          
  #if (DEBOUNCE_MODE)
    //for (j = 0; j < 40; j++) 
    for (j = 0; j < 48; j++) 
    {
      if (switchDebounce[j] > 0) 
      {
        switchDebounce[j] -= 1; // ramp down to zero
      }
    }
  #endif

  // Service MPF again after a complete scan, when all 40 switchStateNow values
  // represent the newest matrix sample.
  serviceOppSerial();

  //delay(10) ; // 10ms loop time
  
  // end read switches

//return;

} // end MAIN LOOP
