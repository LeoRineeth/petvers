# backend.py
import time
import json
import os
import random
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, Tuple

SAVE_FILE = "petverse_pets.json"

# ---------------------------
# Configuration constants
# ---------------------------
HUNGER_INCREASE_PER_HOUR = 2.0
ENERGY_RECOVER_PER_HOUR = 1.0
HAPPINESS_DECAY_PER_HOUR = 0.5
FEED_COST = 5
SHOP_ITEMS = {
    "food": {"price": 5, "hunger_restore": 25, "happiness": 5},
    "toy": {"price": 10, "hunger_restore": 0, "happiness": 20, "energy_cost": 5},
    "energy_drink": {"price": 8, "energy_restore": 30, "happiness": 2},
}

# coin-related defaults
DAILY_REWARD_COINS = 20
JOB_COIN_RATE_PER_MIN = 1 / 5    # 1 coin per 5 minutes
PLAY_COIN_REWARD = 1
REST_COIN_REWARD = 1
RANDOM_GIFT_CHANCE = 0.05        # 5% chance on refresh/status call
RANDOM_GIFT_MIN = 1
RANDOM_GIFT_MAX = 5

class PetFactory:
    TEMPLATES = {
        "cat": {"max_energy": 100, "base_hunger": 30, "base_happiness": 60, "evolve_at": 5, "evolution": "Big Cat"},
        "dog": {"max_energy": 120, "base_hunger": 35, "base_happiness": 55, "evolve_at": 6, "evolution": "Wolfhound"},
        "dragon": {"max_energy": 200, "base_hunger": 20, "base_happiness": 65, "evolve_at": 4, "evolution": "Elder Dragon"},
    }

    @classmethod
    def create_pet(cls, name: str, species: str):
        spec = species.lower()
        template = cls.TEMPLATES.get(spec, cls.TEMPLATES["cat"])
        return Pet(
            name=name,
            species=spec,
            hunger=template["base_hunger"],
            happiness=template["base_happiness"],
            energy=template["max_energy"],
            max_energy=template["max_energy"],
            evolve_at=template["evolve_at"],
            evolution=template["evolution"],
        )

@dataclass
class Pet:
    name: str
    species: str
    hunger: float = 50.0
    happiness: float = 50.0
    energy: float = 100.0
    max_energy: float = 100.0
    level: int = 1
    xp: int = 0
    coins: int = 50
    last_updated: float = field(default_factory=time.time)
    evolve_at: int = 999
    evolution: Optional[str] = None
    evolved: bool = False

    # NEW fields for coin systems / gifts
    last_daily_claim: float = 0.0
    last_gift_time: float = 0.0
    last_gift_amount: int = 0

    def _apply_time_decay(self, seconds: float):
        hours = seconds / 3600.0
        if hours <= 0:
            return
        self.hunger = min(100.0, self.hunger + HUNGER_INCREASE_PER_HOUR * hours)
        self.energy = max(0.0, min(self.max_energy, self.energy + ENERGY_RECOVER_PER_HOUR * hours))
        if self.hunger > 70 or self.energy < 20:
            self.happiness = max(0.0, self.happiness - HAPPINESS_DECAY_PER_HOUR * hours)

    def _maybe_random_gift(self) -> Optional[str]:
        """Small chance to get random coins when pet is refreshed/checked."""
        if random.random() < RANDOM_GIFT_CHANCE:
            amt = random.randint(RANDOM_GIFT_MIN, RANDOM_GIFT_MAX)
            self.coins += amt
            self.last_gift_time = time.time()
            self.last_gift_amount = amt
            return f"Your pet found {amt} coins!"
        return None

    def refresh(self):
        now = time.time()
        elapsed = now - self.last_updated
        if elapsed > 0:
            self._apply_time_decay(elapsed)
            # random gift chance triggers during refresh
            self._maybe_random_gift()
            self.last_updated = now

    # ---- actions ----
    def feed(self, use_item=False, food_strength=20) -> Tuple[bool, str]:
        self.refresh()
        if not use_item:
            if self.coins < FEED_COST:
                return False, "Not enough coins to buy food."
            self.coins -= FEED_COST
        old_hunger = self.hunger
        old_happiness = self.happiness
        self.hunger = max(0.0, self.hunger - food_strength)
        self.happiness = min(100.0, self.happiness + food_strength * 0.2)
        self._gain_xp(10)
        return True, f"Fed {self.name}: hunger {old_hunger:.1f} -> {self.hunger:.1f}"

    def play(self, minutes=10) -> Tuple[bool, str]:
        self.refresh()
        energy_cost = minutes * 0.5
        if self.energy < energy_cost:
            return False, f"{self.name} is too tired to play."
        old_energy = self.energy
        old_happiness = self.happiness
        self.energy = max(0.0, self.energy - energy_cost)
        self.happiness = min(100.0, self.happiness + minutes * 0.6)
        # small coin reward for interaction
        self.coins += PLAY_COIN_REWARD
        self._gain_xp(15 + int(minutes/5))
        return True, f"Played {minutes} min: energy {old_energy:.1f} -> {self.energy:.1f}. +{PLAY_COIN_REWARD} coin."

    def rest(self, minutes=30) -> Tuple[bool, str]:
        self.refresh()
        energy_gain = minutes * 0.8
        old_energy = self.energy
        self.energy = min(self.max_energy, self.energy + energy_gain)
        self.happiness = min(100.0, self.happiness + minutes*0.03)
        # small coin reward for resting
        self.coins += REST_COIN_REWARD
        return True, f"{self.name} rested: energy {old_energy:.1f} -> {self.energy:.1f}. +{REST_COIN_REWARD} coin."

    # ---- leveling / evolution ----
    def _gain_xp(self, amount: int):
        self.xp += amount
        leveled_up = False
        while self.xp >= 100:
            self.xp -= 100
            self.level += 1
            self.coins += 20
            leveled_up = True
        if leveled_up and not self.evolved and self.level >= self.evolve_at:
            self.evolved = True
            return True
        return False

    # ---- new: daily reward ----
    def daily_reward(self) -> Tuple[bool, str]:
        """Give a daily reward if not claimed today."""
        today = time.strftime("%Y-%m-%d", time.localtime())
        last_claim_day = time.strftime("%Y-%m-%d", time.localtime(self.last_daily_claim)) if self.last_daily_claim else None
        if last_claim_day != today:
            self.coins += DAILY_REWARD_COINS
            self.last_daily_claim = time.time()
            return True, f"Daily reward claimed! +{DAILY_REWARD_COINS} coins."
        return False, "Daily reward already claimed today."

    # ---- new: job / work system ----
    def do_job(self, minutes: int = 30) -> Tuple[bool, str]:
        """Send pet to work for minutes; earns coins, costs some energy, gives small XP."""
        self.refresh()
        if minutes <= 0:
            return False, "Invalid job duration."
        energy_cost = minutes * 0.3
        if self.energy < energy_cost:
            return False, f"{self.name} is too tired to work. Needs more energy."
        earned = int(minutes * JOB_COIN_RATE_PER_MIN)
        self.energy = max(0.0, self.energy - energy_cost)
        self.coins += earned
        xp_gain = max(1, minutes // 10)
        self._gain_xp(xp_gain)
        return True, f"{self.name} worked for {minutes} mins and earned {earned} coins."

    # ---- shop usage helper ----
    def buy_item(self, item_key: str) -> Tuple[bool, str]:
        item = SHOP_ITEMS.get(item_key)
        if not item:
            return False, "Invalid item."
        if self.coins < item["price"]:
            return False, "Not enough coins."
        self.coins -= item["price"]
        if item_key == "food":
            self.hunger = max(0.0, self.hunger - item["hunger_restore"])
            self.happiness = min(100.0, self.happiness + item.get("happiness", 0))
            self._gain_xp(5)
            return True, f"Used food. Hunger -> {self.hunger:.1f}"
        elif item_key == "toy":
            energy_cost = item.get("energy_cost", 0)
            if self.energy < energy_cost:
                self.coins += item["price"]
                return False, f"{self.name} is too tired to use the toy."
            self.energy = max(0.0, self.energy - energy_cost)
            self.happiness = min(100.0, self.happiness + item["happiness"])
            self._gain_xp(10)
            return True, f"Played with toy. Energy -> {self.energy:.1f}"
        elif item_key == "energy_drink":
            self.energy = min(self.max_energy, self.energy + item["energy_restore"])
            self.happiness = min(100.0, self.happiness + item.get("happiness", 0))
            self._gain_xp(7)
            return True, f"Drank energy drink. Energy -> {self.energy:.1f}"
        return False, "Unknown item effect."

    def status(self) -> Dict:
        """Return current status and trigger refresh + possible random gift. Includes recent gift info."""
        self.refresh()
        gift_msg = None
        # If a gift was received in the last refresh, include it in status:
        if self.last_gift_time and (time.time() - self.last_gift_time) < 5.0:
            gift_msg = f"Found {self.last_gift_amount} coins!"
        return {
            "name": self.name,
            "species": self.species,
            "evolution": self.evolution if self.evolved else self.species,
            "hunger": round(self.hunger, 1),
            "happiness": round(self.happiness, 1),
            "energy": round(self.energy, 1),
            "level": self.level,
            "xp": self.xp,
            "coins": self.coins,
            "last_updated": time.ctime(self.last_updated),
            "gift_message": gift_msg,
            "last_daily_claim": time.ctime(self.last_daily_claim) if self.last_daily_claim else None,
        }

    # serialization helpers
    def to_dict(self):
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name"),
            species=data.get("species"),
            hunger=data.get("hunger", 50.0),
            happiness=data.get("happiness", 50.0),
            energy=data.get("energy", data.get("max_energy", 100.0)),
            max_energy=data.get("max_energy", 100.0),
            level=data.get("level", 1),
            xp=data.get("xp", 0),
            coins=data.get("coins", 50),
            last_updated=data.get("last_updated", time.time()),
            evolve_at=data.get("evolve_at", 999),
            evolution=data.get("evolution"),
            evolved=data.get("evolved", False),
            last_daily_claim=data.get("last_daily_claim", 0.0),
            last_gift_time=data.get("last_gift_time", 0.0),
            last_gift_amount=data.get("last_gift_amount", 0),
        )

class PetWorld:
    def __init__(self):
        self.pets: Dict[str, Pet] = {}
        # try to auto-load on create
        if os.path.exists(SAVE_FILE):
            self.load(SAVE_FILE)

    def create_pet(self, name: str, species: str) -> Tuple[bool, str]:
        name = name.strip()
        if not name:
            return False, "Pet name cannot be empty."
        if name in self.pets:
            return False, "A pet with that name already exists."
        pet = PetFactory.create_pet(name, species)
        self.pets[name] = pet
        return True, f"Pet '{name}' the {species} created."

    def get_pet(self, name: str) -> Optional[Pet]:
        return self.pets.get(name)

    def delete_pet(self, name: str) -> bool:
        if name in self.pets:
            del self.pets[name]
            return True
        return False

    def save(self, filename=SAVE_FILE):
        data = {name: pet.to_dict() for name, pet in self.pets.items()}
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        return filename

    def load(self, filename=SAVE_FILE):
        if not os.path.exists(filename):
            return False, "No save file found."
        with open(filename, "r") as f:
            raw = json.load(f)
        for name, pdata in raw.items():
            pet = Pet.from_dict(pdata)
            try:
                pet.last_updated = float(pdata.get("last_updated", time.time()))
            except:
                pet.last_updated = time.time()
            self.pets[name] = pet
        return True, f"Loaded {len(self.pets)} pets."
