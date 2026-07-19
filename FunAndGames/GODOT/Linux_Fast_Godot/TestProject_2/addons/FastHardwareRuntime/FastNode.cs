// FastNode.cs — loose wrapper script for the FAST hardware runtime.
//
// WHY THIS FILE EXISTS
//   FastHardwareRuntime ships as a *precompiled DLL*. Godot 4 only lists a [GlobalClass] in the
//   "Add Node" dialog (and only accepts a class as an Autoload target) when the class is backed by
//   a script FILE inside the project's res:// filesystem — a type that lives only in a referenced
//   DLL does not qualify. This three-line subclass provides that script file. It inherits every
//   Gd* method and both signals (HardwareReady, SwitchActivity) from FAST_Pinball.FAST.
//
// WHERE IT GOES
//   Drop this file anywhere in your Godot project, e.g.
//       res://addons/FastHardwareRuntime/FastNode.cs
//   then Build. It requires the same <Reference> to FastHardwareRuntime.dll that the README sets up.
//
// HOW TO USE IT (pick one)
//   • Add Node dialog:  after building, "FastNode" appears in Add Node — add it to a scene.
//   • Autoload (recommended for GDScript): Project ▸ Project Settings ▸ Autoload, add this script
//     with the node name "Fast". Every .gd script can then call Fast.GdStartup(...) globally with
//     no node to place. See TestMain.gd for the autoload version, or project-autoload.txt.
//
//   Pure-C# projects usually need none of this: FAST.Startup(...) now self-spawns its own node.

using Godot;

[GlobalClass]
public partial class FastNode : FAST_Pinball.FAST { }
