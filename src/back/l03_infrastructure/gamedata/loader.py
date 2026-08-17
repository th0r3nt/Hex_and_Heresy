
# В JSON файлах геймдаты не должно быть «магических строк». Там должны быть уникальные строковые идентификаторы (ID). 

# При запуске игры твой бэкенд (в слое `l03_infrastructure/gamedata/loader.py`) делает следующее:
# 1. Читает все файлы `weapons.json`, `armor.json` и валидирует их через Pydantic. Сохраняет в словарь (Registry) в памяти: `{"wpn_hum_halberd_02": WeaponModel(...)}`.
# 2. Читает `units.json`. Видит там ID оружия.
# 3. Проверяет, есть ли такой ID в реестре оружия. Если нет — бросает ошибку при запуске сервера (FastAPI падает с понятным логом "Weapon ID not found").

# Вот как должны выглядеть эти файлы по-хорошему.

# 1. Файл экипировки (например: `gamedata/factions/humans/equipment/weapons.json`)
# Здесь мы описываем сами объекты как самостоятельные сущности.

# [
#   {
#     "id": "weapon_human_halberd_02",
#     "type": "melee_2h",
#     "name": "Стальная алебарда",
#     "tier": 2,
#     "stats": {
#       "damage": 15,
#       "armor_piercing": 5,
#       "initiative_penalty": 1
#     },
#     "lore_description": "Тяжелое оружие городской стражи."
#   },
#   {
#     "id": "weapon_human_arquebus_02",
#     "type": "ranged_2h",
#     "name": "Тяжелая аркебуза",
#     "tier": 2,
#     "stats": {
#       "damage": 30,
#       "armor_piercing": 50,
#       "range": 5
#     },
#     "lore_description": "Громко, больно. Пахнет серой."
#   }
# ]


# 2. Файл юнитов (например: `gamedata/factions/humans/units/classic.json`)
# А вот тут мы используем только ID для связи. Никакого хардкода свойств оружия.

# [
#   {
#     "id": "unit_human_ironsides",
#     "name": "Железнобокие",
#     "tier": 2,
#     "base_stats": {
#       "unit_count": 80,
#       "hp_per_unit": 20,
#       "morale": 75,
#       "movement_speed": 1
#     },
#     "default_equipment": {
#       "weapon_id": "weapon_human_halberd_02",
#       "armor_id": "armor_human_cuirass_02",
#       "accessory_id": null
#     },
#     "lore_description": "Универсальная тяжелая пехота Империи."
#   }
# ]
