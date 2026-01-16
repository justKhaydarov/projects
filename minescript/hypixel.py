from minescript import (echo, execute, getblock, player)
import sys

# Get the player's position, rounded to the nearest integer:
x, y, z = [round(p) for p in player().position]

# Get the type of block directly beneath the player:
block_type = getblock(x, y - 1, z)
block_type = block_type.replace("minecraft:", "").split("[")[0]

sign_text = (
    """{Text1:'{"text":"%s"}',Text2:'{"text":"at"}',Text3:'{"text":"%d %d %d"}'}""" %
    (block_type, x, y - 1, z))

# Script argument, passed from Minecraft like "example 5"
rotation = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if rotation < 0 or rotation > 15:
  raise ValueError(f"Param not an integer between 0 and 15: {rotation}")

# Create a sign then set text on it:
execute(f"/setblock {x} {y} {z} minecraft:birch_sign[rotation={rotation}]")
execute(f"/data merge block {x} {y} {z} {sign_text}")

# Write a message to the chat that 
echo(f"Created sign at {x} {y} {z} over {block_type}")