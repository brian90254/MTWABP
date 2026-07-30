extends Node3D
#
# TestMain.gd — the GDScript twin of TestMain.cs.
#
# Setup (one-time):
#   1. Install the FastHardwareRuntime addon and build the project (it is a .NET/C# Godot project;
#      the compiled DLL cannot load in a GDScript-only Godot build).
#   2. Copy FastNode.cs (from this Examples folder) into the project and Build. This loose script is
#      what lets GDScript reach the DLL type; the DLL alone cannot be autoloaded or added as a node.
#   3. Autoload FastNode under the name "Fast" (Project Settings ▸ Autoload). See project-autoload.txt.
#   4. Attach this script to a Node3D in your scene.
#
# GDScript reaches the hardware through the autoloaded FAST node's Gd* methods and its two signals
# (HardwareReady, SwitchActivity) — see FAST_GodotScript.cs in the plugin. The underlying C# API is
# static, which GDScript cannot call directly; the Gd* wrappers bridge that gap.
#
# (Prefer a per-scene child node instead of an autoload? Add a "FastNode" via the Add Node dialog,
#  then replace `Fast` below with `$FastNode`.)

# --- FAST enum values (mirrors FAST_Pinball.FAST — these indices are fixed by the C# enums) ---
const NODE_FP_CAB0001 := 0    # eNodeBoards.FP_CAB0001
const EXP_NEURON      := 0    # eExpansionBoards.NEURON

const DEST_NEURON     := 0    # eExpansionDestinations.NEURON
const DEST_EXPANSION  := 1    # eExpansionDestinations.EXPANSION

const NET_UNKNOWN     := 0    # eNetStyle.UNKNOWN
const NET_STUB        := 1    # eNetStyle.STUB
const NET_MODERN      := 2    # eNetStyle.MODERN
const NET_RETRO_11    := 3    # eNetStyle.RETRO_11
const NET_RETRO_89    := 4    # eNetStyle.RETRO_89
const NET_RETRO_95    := 5    # eNetStyle.RETRO_95

const RESULT_SUCCESS  := 0    # eResult.SUCCESS

# The FAST hardware node — the "Fast" autoload singleton (see project-autoload.txt).
# @onready var _fast: Node3D = Fast
@onready var _fast = Fast

var _colour_time: float = 0.0
var _pixel_array: PackedColorArray = PackedColorArray()


func _ready() -> void:
	_pixel_array.resize(10)

	print("Has HardwareReady signal: ", _fast.has_signal("HardwareReady"))
	print("Has SwitchActivity signal: ", _fast.has_signal("SwitchActivity"))

	var ready_error = _fast.connect(
		"HardwareReady",
		Callable(self, "_on_hardware_ready")
	)

	var switch_error = _fast.connect(
		"SwitchActivity",
		Callable(self, "_on_switch_activity")
	)

	print("HardwareReady connect result: ", ready_error)
	print("SwitchActivity connect result: ", switch_error)
	print(
		"HardwareReady connected: ",
		_fast.is_connected(
			"HardwareReady",
			Callable(self, "_on_hardware_ready")
		)
	)

	call_deferred("_start_fast")

	print(">>>> Leaving _ready()")

func _start_fast() -> void:
	print(">>>> Entering _start_fast()")

	var result = _fast.GdStartup(
		PackedInt32Array([3,1]),
		#PackedInt32Array(),
		PackedInt32Array([0,3]),
		#PackedInt32Array(),
		false
	)

	print("GdStartup returned: ", result)
	print("GdIsInitialized immediately after startup: ", _fast.GdIsInitialized())
	print("Machine type immediately after startup: ", _fast.GdGetMachineType())
	print(">>>> Leaving _start_fast()")

func _process(delta: float) -> void:
	# If the system hasn't started up yet, don't do anything.
	if not _fast.GdIsInitialized():
		#print("Not initialized yet")
		return

	print("Initialized!")

	_colour_time += delta
	if _colour_time < 0.5:
		for i in _pixel_array.size():
			_pixel_array[i] = Color.WHITE if (i & 0x01) != 0 else Color.BLACK
	else:
		for i in _pixel_array.size():
			_pixel_array[i] = Color.BLACK if (i & 0x01) != 0 else Color.WHITE

	if _colour_time > 1.0:
		_colour_time -= 1.0

	# Update the hardware with the new pixels.
	_fast.GdSetPixelColours(0, _pixel_array, DEST_NEURON)
	_fast.GdSetPixelColour(20, Color(_colour_time, 0, _colour_time), DEST_NEURON)

	# Quitting the game.
	if Input.is_physical_key_pressed(KEY_ESCAPE):
		_fast.GdTurnOffPixels(DEST_NEURON)
		get_tree().quit()


func _on_hardware_ready(result_code: int) -> void:
	print(">>>> ENTERED _on_hardware_ready")
	print("HardwareReady result_code: ", result_code)

	var machine_type = _fast.GdGetMachineType()
	print("Machine type code: ", machine_type)

	match machine_type:
		NET_STUB:
			print("Found Hardware STUB")
		NET_MODERN:
			print("Found Hardware NEURON")
		NET_RETRO_11:
			print("Found Hardware SYSTEM 11")
		NET_RETRO_89:
			print("Found Hardware WPC 89")
		NET_RETRO_95:
			print("Found Hardware WPC 95")
		_:
			print("Unknown Hardware: ", machine_type)

	print("Is initialized: ", _fast.GdIsInitialized())
	print(">>>> Leaving _on_hardware_ready")


func _on_switch_activity(switch_index: int, switch_event: int) -> void:
	# switch_event is a FAST.eSwitchEvent value (1 == ON_DOWN/CLOSED, 2 == ON_UP/OPENED).
	print("Switch %d is now %d" % [switch_index, switch_event])
