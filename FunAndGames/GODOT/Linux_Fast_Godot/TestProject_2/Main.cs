using System.Collections;
using System.Collections.Generic;

using Godot;

using FAST_Pinball;


public partial class Main: Node3D
{
 float ColourTime;
 
 Color[] PixelArray;
 
 // public TextMesh HardwareText;
 // public TextMesh ConsoleText;
 Queue<string>   ConsoleLines;
  
 // Start is called before the first frame update
 public override void _Ready()
 {
  //if (HardwareText != null)
  //  HardwareText.gameObject.SetActive(false);
	
  PixelArray = new Color[10];
  
  // Console echo
  //if (ConsoleText != null)
  //  ConsoleText.text = "";
  ConsoleLines = new Queue<string>();
  
  //Application.logMessageReceived += EchoDebugMessage;
  
  GD.Print(">>>>Runtime - Initializing Fast hardware...");
  FAST_Pinball.FAST.Startup(FastInitializationCompleteCallback, 
  
							// Ordered list of Node boards
							new List<FAST_Pinball.FAST.eNodeBoards>()      
							   {
								FAST_Pinball.FAST.eNodeBoards.FP_CAB0001
							   }, 
							   
							// Ordered list of expansion boards
							new List<FAST_Pinball.FAST.eExpansionBoards>()
							   {
								FAST_Pinball.FAST.eExpansionBoards.NEURON
							   },
							false);
 }

 // Update is called once per frame
 public override void _Process(double delta)
 {
  // If the system hasn't started up yet, don't do anything
  if (!FAST_Pinball.FAST.IsInitialized())
	return;

  ColourTime += (float)delta;
  if (ColourTime < 0.5f)
	{
	 for (int i=0; i<PixelArray.Length; ++i)
	   PixelArray[i] = ((i&0x01)!=0)?Colors.White:Colors.Black;
	}
  else
	{
	 for (int i=0; i<PixelArray.Length; ++i)
	   PixelArray[i] = ((i&0x01)!=0)?Colors.Black:Colors.White;
	}
	  
  if (ColourTime > 1.0f)
	ColourTime -= 1.0f;
  
  // Update the hardware with the new pixels
  FAST_Pinball.FAST.SetPixelColours(0, PixelArray);
  FAST_Pinball.FAST.SetPixelColour(20, new Color(ColourTime, 0, ColourTime), FAST_Pinball.FAST.eExpansionDestinations.NEURON);

  // Quitting the game
  if (Input.IsPhysicalKeyPressed(Key.Escape))
	{
	 FAST_Pinball.FAST.TurnOffPixels(FAST_Pinball.FAST.eExpansionDestinations.NEURON);
	 GetTree().Quit();
	}
 }
 
 
 void FastInitializationCompleteCallback(FAST_Pinball.FAST.eResult Success)
 {
  GD.Print(">>>>Runtime - Fast is ready, now setting up drivers...");
  
  // Hardware text
  string HardwareConsoleOutput = "";

  if (FAST_Pinball.FAST.IsMachine_RETRO_11())
	HardwareConsoleOutput = "Found Hardware SYSTEM 11";
  else if (FAST_Pinball.FAST.IsMachine_RETRO_89())
	HardwareConsoleOutput = "Found Hardware WPC 89";
  else if (FAST_Pinball.FAST.IsMachine_RETRO_95())
	HardwareConsoleOutput = "Found Hardware WPC 95";
  else if (FAST_Pinball.FAST.IsMachine_MODERN())
	HardwareConsoleOutput = "Found Hardware NEURON";
  else 
	HardwareConsoleOutput = "Unknown Hardware";
  
//  if (HardwareText != null)
//   {
//    HardwareText.text = HardwareConsoleOutput;
//   HardwareText.gameObject.SetActive(true);
//  }

  // Assign a spoof key to switch 0
  FAST_Pinball.FAST.RegisterSpoofKey(0, Key.A);
  
  // Assign an event callback for switch 0
  FAST_Pinball.FAST.RegisterSwitchCallback(0, SwitchTestCallback);
  
  // Set all pixels a colour now
  FAST_Pinball.FAST.SetAllPixelsToColour(new Color(0.0f, 1.0f, 0.0f), FAST_Pinball.FAST.eExpansionDestinations.NEURON);

  // Done!
  GD.Print(">>>>Runtime - Initialization Complete");
 }


 void SwitchTestCallback(int SwitchIndex, FAST_Pinball.FAST.eSwitchEvent SwitchEvent)
 {
  GD.Print("Switch " + SwitchIndex + " is now " + SwitchEvent.ToString());
 }
}
