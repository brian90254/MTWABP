extends Area2D

@onready var game_manager: Node = %GameManager

## Called when the node enters the scene tree for the first time.
#func _ready() -> void:
	##pass # Replace with function body.
	#print("I'm a coin.")
#
#
## Called every frame. 'delta' is the elapsed time since the previous frame.
#func _process(delta: float) -> void:
	#pass


func _on_body_entered(body: Node2D) -> void:
	#pass # Replace with function body.
	game_manager.add_point()
	print ("+1 coin")
	queue_free()
	
