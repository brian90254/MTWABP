extends Area2D

@onready var timer: Timer = $Timer

func _on_body_entered(body: Node2D) -> void:
	#pass # Replace with function body.
	print("You Died!")
	body.get_node("CollisionShape2D").queue_free()
	Engine.time_scale = 0.5
	timer.start()
	
func _on_timer_timeout() -> void:
	#pass # Replace with function body.
	Engine.time_scale = 1
	get_tree().reload_current_scene()
	
