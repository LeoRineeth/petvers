from flask import Flask, render_template, request, redirect, url_for, flash
from backend import PetWorld, SHOP_ITEMS

app = Flask(__name__)
app.secret_key = "perverse-secret-key"  # required for flash messages

# create global world object
world = PetWorld()


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def index():
    pets = [p.status() for p in world.pets.values()]
    return render_template("index.html", pets=pets)


# -----------------------------
# CREATE PET
# -----------------------------
@app.route("/create", methods=["POST"])
def create():
    name = request.form.get("name", "").strip()
    species = request.form.get("species", "cat").strip().lower()

    ok, msg = world.create_pet(name, species)
    flash(msg)

    if ok:
        world.save()

    return redirect(url_for("index"))


# -----------------------------
# PET DETAILS PAGE
# -----------------------------
@app.route("/pet/<name>")
def pet_page(name):
    pet = world.get_pet(name)
    if not pet:
        flash("Pet not found.")
        return redirect(url_for("index"))

    return render_template("pet.html", pet=pet.status(), shop=SHOP_ITEMS)


# -----------------------------
# FEED PET
# -----------------------------
@app.route("/pet/<name>/feed", methods=["POST"])
def feed(name):
    pet = world.get_pet(name)
    if not pet:
        flash("Pet not found.")
        return redirect(url_for("index"))

    ok, msg = pet.feed()
    flash(msg)

    if ok:
        world.save()

    return redirect(url_for("pet_page", name=name))


# -----------------------------
# PLAY WITH PET
# -----------------------------
@app.route("/pet/<name>/play", methods=["POST"])
def play(name):
    pet = world.get_pet(name)
    if not pet:
        flash("Pet not found.")
        return redirect(url_for("index"))

    minutes = int(request.form.get("minutes", 10))
    ok, msg = pet.play(minutes)

    flash(msg)
    if ok:
        world.save()

    return redirect(url_for("pet_page", name=name))


# -----------------------------
# PET REST
# -----------------------------
@app.route("/pet/<name>/rest", methods=["POST"])
def rest(name):
    pet = world.get_pet(name)
    if not pet:
        flash("Pet not found.")
        return redirect(url_for("index"))

    minutes = int(request.form.get("minutes", 30))
    ok, msg = pet.rest(minutes)

    flash(msg)
    if ok:
        world.save()

    return redirect(url_for("pet_page", name=name))


# -----------------------------
# BUY SHOP ITEM
# -----------------------------
@app.route("/pet/<name>/buy", methods=["POST"])
def buy(name):
    pet = world.get_pet(name)
    if not pet:
        flash("Pet not found.")
        return redirect(url_for("index"))

    item_key = request.form.get("item_key")
    ok, msg = pet.buy_item(item_key)

    flash(msg)
    if ok:
        world.save()

    return redirect(url_for("pet_page", name=name))


# -----------------------------
# DAILY REWARD
# -----------------------------
@app.route("/pet/<name>/daily", methods=["POST"])
def daily_reward(name):
    pet = world.get_pet(name)
    if not pet:
        flash("Pet not found.")
        return redirect(url_for("index"))

    ok, msg = pet.daily_reward()
    flash(msg)

    if ok:
        world.save()

    return redirect(url_for("pet_page", name=name))


# -----------------------------
# JOB / WORK SYSTEM
# -----------------------------
@app.route("/pet/<name>/work", methods=["POST"])
def work(name):
    pet = world.get_pet(name)
    if not pet:
        flash("Pet not found.")
        return redirect(url_for("index"))

    minutes = int(request.form.get("minutes", 30))
    ok, msg = pet.do_job(minutes)

    flash(msg)
    if ok:
        world.save()

    return redirect(url_for("pet_page", name=name))


# -----------------------------
# DELETE PET
# -----------------------------
@app.route("/pet/<name>/delete", methods=["POST"])
def delete(name):
    ok = world.delete_pet(name)
    if ok:
        world.save()
        flash("Pet deleted.")
    else:
        flash("Pet not found.")
    return redirect(url_for("index"))


# Run server
if __name__ == "__main__":
    app.run(debug=True)
