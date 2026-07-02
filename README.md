# Hex & Heresy

**Hex & Heresy** is a turn-based grand tactical strategy game combining 4X elements, grid-based tactical battles, and role-playing interaction powered by Large Language Models (LLMs). The project is currently in the Minimum Viable Product (MVP) development stage.

---

## General Concept and Game World

The game is set in an original dark post-apocalyptic fantasy setting. In the era of the "Long Winter," the remnants of civilizations survive on a planet devastated by the impact of a celestial body known as "The Progenitor." 

The cataclysm altered Earth's physical constants:
* **Astronomical shifts:** The day cycle has stretched to 28 hours, divided into safe *Grey Hours* and psychologically unstable *Neon Hours*, illuminated by residual radiation.
* **Magical radiation:** Magic is represented by an isotope called *Resonite*—an information-receptive matter. Its use leads to biological mutations ("cursed genes") and contaminates the atmosphere with toxic dust ("primordial suspension").
* **Geographical zones:** The game world is divided into protected Citadels (bases), adjacent allied lands, and anomalous neutral regions (No Man's Lands), which harbor resources and artifacts of bygone eras.

---

## System Architecture

The project is divided into two isolated interaction layers to prevent game state desynchronization:

```
┌────────────────────────┐              ┌────────────────────────┐
│   Frontend (Electron)  │ ◄── JSON ──► │    Backend (Python)    │
│  - "Dumb terminal"     │              │  - Game logic          │
│  - UI / DOM rendering  │              │  - Async LLM APIs      │
│  - Grid and animation  │              │  - Pydantic validation │
└────────────────────────┘              └────────────────────────┘
```

1. **Backend (Python):**
   * Processes battle mathematics, movement, economic calculations, and turn cycles.
   * Relies on strict type definitions and world state (`WorldState`) validation via the `Pydantic` library.
   * Interacts asynchronously with external LLM APIs, preventing the main execution thread from blocking during text response generation.
2. **Frontend (TypeScript/JS, CSS, HTML in Electron container):**
   * Functions as a "thin client." It receives structured JSON data from the backend and updates the interface state.
   * In the MVP phase, it utilizes text characters, emojis, and CSS styling to render the hexagonal map and tactical grid.

---

## Core Game Mechanics

### 1. Text-Based Diplomacy and AI Commanders
* **Modular Prompt Assembly:** The personality of each AI opponent is generated dynamically using a constructor script. The prompt combines general behavior rules, racial traits, basic action patterns, and a specific archetype (e.g., *Strategist*, *Paranoid*, or *Warmonger*).
* **Free-text messaging:** Communication with AI leaders is implemented via text dispatches and ambassadors on the global map. The models accept free-text input from the player and react according to their personality traits.
* **JSON Control:** Model responses contain instructions in JSON format. Using *Function Calling* tools, the AI executes actual in-game actions: declaring war, offering resource trades, or demanding tribute.

### 2. Tactical Grid Battles
* **Tactical Field:** Combat is simulated on a rectangular $20 \times 20$ grid, where each squad occupies a single position.
* **Physics and Positioning:** The system calculates movement speed, stamina, attack direction (flank, rear), and charge damage, which depends on the speed difference between colliding squads.
* **Terrain and Environmental Factors:** Tactical advantage is influenced by high ground, mud, marshland, night time, and weather conditions (e.g., rain preventing the use of gunpowder weapons).
* **Heaps of Corpses:** Mass casualties in a specific area of the tactical field deform the terrain, creating blockades of bodies that reduce movement speed and provide new tactical opportunities for necromancers.

### 3. Economy and Troop Assembly
* **Risk Management:** Allocating workers (tier 00 units) between safe resource gathering at the base, moderately dangerous work in allied lands, and expeditions into neutral zones.
* **Equipment Designer:** The stats of combat squads are formed based on their basic racial archetype, selected weapon, armor type, and additional accessories.
* **Looting:** After battles, surviving squads or workers can scavenge equipment left on the battlefield. Loot is converted according to faction rules: humans can melt down foreign gear into resources or faith points, greenskins modify it to their standards, and mercenaries sell it on the black market.

### 4. Equipment Designer ("Weaponsmith")
* A unique in-game interface allows players to describe desired equipment in plain text. 
* The weaponsmith model analyzes the request for lore friendliness, calculates balanced stats, assigns a tier, determines the production cost in materials, and creates a new equipment card available for the faction's squads to equip.

### 5. Unit Progression and Veteran System
* Upon recruitment, basic squads are non-personalized combat units without LLM integration.
* Upon achieving key tactical milestones (surviving critical losses, destroying an elite unit, capturing a citadel), a squad receives the status of a **named** unit.
* For named units, a commander's personality, a backstory of their exploit, and unique character traits are generated. The player gains the ability to communicate directly with veterans, who may demand a pay raise, refuse unfavorable tactical maneuvers, or request specific equipment.

---

## Game Factions

| Faction | Gameplay Features | Technological Focus |
| :--- | :--- | :--- |
| **Humans (Empire)** | Rigid discipline, use of militia. Cannot tolerate magic. | Regular army, gunpowder weapons, inquisition. |
| **Greenskins** | High numbers, horde mechanics (bonuses for the number of allies). | Handcrafted engineering, shamanism, taming of wild monsters. |
| **Elves** | High initiative and high unit cost. | Crystal weaponry, illusions, harvesting resonite from the fallen. |
| **Baronal Forces** | Economic pressure, collecting duties from neutral territories. | Defensive castles, crossbows, heavy plate armor. |
| **Brigands** | Sacrificial mechanics, no concept of the value of life. | Necromancy, demon summoning, manipulation of the bodies of the fallen. |
| **Mercenaries** | Unique contracts on the global map, high mobility. | Airships, professional heavy infantry. |