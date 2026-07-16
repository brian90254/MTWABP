using System.Collections.Generic;
using Godot;
using FAST_Pinball;

public partial class main : Node3D
{
	public override void _Ready()
	{
		GD.Print("Calling FAST startup...");

		FAST.Startup(
			OnFastInitialized,
			new List<FAST.eNodeBoards>
			{
				FAST.eNodeBoards.FP_CAB0001
			},
			new List<FAST.eExpansionBoards>
			{
				FAST.eExpansionBoards.NEURON
			},
			false
		);
	}

	private void OnFastInitialized(FAST.eResult result)
	{
		GD.Print("FAST callback result: ", result);

		FAST.RegisterSpoofKey(0, Key.A);
		FAST.RegisterSwitchCallback(0, OnSwitchChanged);
	}

	private void OnSwitchChanged(
		int switchIndex,
		FAST.eSwitchEvent switchEvent)
	{
		GD.Print($"Switch {switchIndex} is now {switchEvent}");
	}
}
