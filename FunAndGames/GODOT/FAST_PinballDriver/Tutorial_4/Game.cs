using Godot;
using System;
using FAST_Pinball;

//var fast = new FAST()

	
public partial class Game : Node2D
{
	// Called when the node enters the scene tree for the first time.
	public override void _Ready()
	{
		GD.Print("FAST library loaded!");
		
		// FAST fast = new FAST();
	}

	// Called every frame. 'delta' is the elapsed time since the previous frame.
	public override void _Process(double delta)
	{
	}
}
