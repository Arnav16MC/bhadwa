from flask import Flask, request, jsonify
import random
import threading
import time

app = Flask(__name__)

rooms = {}  # room_id: room_data

# Room data structure:
# {
#   "players": {player_name: {"is_bhadwa": bool, "voted_today": bool}},
#   "bhadwa": player_name,
#   "votes": {player_name: vote_count},
#   "game_active": True,
#   "result": None
# }

VOTING_PERIOD_SECONDS = 24 * 60 * 60  # 1 day voting period


def end_voting(room_id):
    """Ends voting after voting period."""
    room = rooms.get(room_id)
    if not room or not room["game_active"]:
        return
    room["game_active"] = False

    votes = room["votes"]
    if not votes:
        room["result"] = "No votes cast. No elimination."
        return

    # Find who got most votes
    max_votes = max(votes.values())
    candidates = [p for p, v in votes.items() if v == max_votes]

    # Eliminate randomly if tie
    eliminated = random.choice(candidates)

    # If eliminated is bhadwa, innocents win
    if eliminated == room["bhadwa"]:
        room["result"] = f"Bhadwa {eliminated} was eliminated. Innocents win!"
    else:
        room["result"] = f"{eliminated} was eliminated. Bhadwa wins."


@app.route("/")
def index():
    return "Welcome to the Bhadwa Game API! Use /create_room, /vote, /status endpoints."


@app.route("/create_room", methods=["POST"])
def create_room():
    data = request.get_json()
    room_id = data.get("room_id")
    player_names = data.get("player_names")  # list of strings

    if not room_id or not player_names:
        return jsonify({"error": "room_id and player_names required"}), 400

    if len(player_names) < 2 or len(player_names) > 20:
        return jsonify({"error": "Number of players must be between 2 and 20"}), 400

    if len(set(player_names)) != len(player_names):
        return jsonify({"error": "Player names must be unique"}), 400

    # Assign bhadwa randomly
    bhadwa = random.choice(player_names)

    # Initialize room data
    rooms[room_id] = {
        "players": {name: {"is_bhadwa": name == bhadwa, "voted_today": False} for name in player_names},
        "bhadwa": bhadwa,
        "votes": {},
        "game_active": True,
        "result": None
    }

    # Start voting period timer in a background thread
    threading.Thread(target=lambda: (time.sleep(VOTING_PERIOD_SECONDS), end_voting(room_id))).start()

    return jsonify({"message": f"Room {room_id} created with players.", "bhadwa": bhadwa})


@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()
    room_id = data.get("room_id")
    voter = data.get("voter")
    vote_for = data.get("vote_for")

    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room does not exist"}), 404

    if not room["game_active"]:
        return jsonify({"error": "Voting period has ended", "result": room.get("result")})

    if voter not in room["players"]:
        return jsonify({"error": "Voter not in room"}), 400

    if vote_for not in room["players"]:
        return jsonify({"error": "Vote target not in room"}), 400

    if room["players"][voter]["voted_today"]:
        return jsonify({"error": "You have already voted today"}), 400

    # Record vote
    room["players"][voter]["voted_today"] = True
    room["votes"][vote_for] = room["votes"].get(vote_for, 0) + 1

    return jsonify({"message": f"{voter} voted for {vote_for}"})


@app.route("/reset_votes", methods=["POST"])
def reset_votes():
    """Reset daily voting status for all players in a room. Call once per day to allow new voting."""
    data = request.get_json()
    room_id = data.get("room_id")
    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room does not exist"}), 404

    if not room["game_active"]:
        return jsonify({"error": "Game has ended", "result": room.get("result")})

    for p in room["players"].values():
        p["voted_today"] = False

    return jsonify({"message": "Votes reset, new day started"})


@app.route("/status", methods=["GET"])
def status():
    room_id = request.args.get("room_id")
    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room does not exist"}), 404

    info = {
        "players": list(room["players"].keys()),
        "bhadwa": room["bhadwa"],
        "votes": room["votes"],
        "game_active": room["game_active"],
        "result": room.get("result")
    }
    return jsonify(info)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
