"""Hilfsfunktionen für Gegner und deren Rennverhalten."""

import random
import streamlit as st

from car import Car


# Mögliche Teams für die KI-Gegner.
TEAM_POOL = ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams']

# Die Werte bleiben bewusst einfach: Sie geben eine Wahrscheinlichkeit an, mit der ein Team mit einem
# bestimmten Startreifen ins Rennen geht. So haben wir etwas variierende Gegner mit verschiedenen Profilen.
BASE_STARTING_TIRE_WEIGHTS = {
    'Ferrari': [('SOFT', 0.55), ('MEDIUM', 0.35), ('HARD', 0.10)],
    'Mercedes': [('SOFT', 0.20), ('MEDIUM', 0.50), ('HARD', 0.30)],
    'Red Bull': [('SOFT', 0.35), ('MEDIUM', 0.45), ('HARD', 0.20)],
    'McLaren': [('SOFT', 0.45), ('MEDIUM', 0.40), ('HARD', 0.15)],
    'Williams': [('SOFT', 0.20), ('MEDIUM', 0.40), ('HARD', 0.40)],
}

# Typisches Boxenfenster je Team als Anteil der Renndistanz womit den Gegnern Profile verpasst werden.
BASE_PIT_FRACTION_PROFILES = {
    'Ferrari': 0.45,
    'Mercedes': 0.48,
    'Red Bull': 0.40,
    'McLaren': 0.38,
    'Williams': 0.50,
}

# Der Startreifen bestimmt die Strategie stark mit: weich = früher Stopp, hart = späterer Stopp.
STARTING_TIRE_STRATEGIES = {
    'SOFT': {
        'pit_fraction_factor': 0.60,
        'next_compound_weights': [('MEDIUM', 0.45), ('HARD', 0.55)],
    },
    'MEDIUM': {
        'pit_fraction_factor': 0.80,
        'next_compound_weights': [('SOFT', 0.15), ('HARD', 0.85)],
    },
    'HARD': {
        'pit_fraction_factor': 1.15,
        'next_compound_weights': [('SOFT', 0.25), ('MEDIUM', 0.75)],
    },
}

# Reifenalter- und Event-Schwellwerte steuern, wie früh ein Gegner sinnvoll stoppen kann.

MIN_EVENT_PIT_AGE_SC = {
    'SOFT': 7,
    'MEDIUM': 10,
    'HARD': 12,
}

MIN_EVENT_PIT_AGE_VSC = {
    'SOFT': 10,
    'MEDIUM': 14,
    'HARD': 20,
}

class Opponent:
    """Ein KI-Gegner mit Auto und einfacher Strategie."""

    def __init__(self, team, car, starting_tire, pit_lap, next_compound):
        """Speichert Team, Auto und geplante Stoppdaten."""
        # Jeder Gegner speichert nur die Daten, die wir für das Rennen brauchen.
        self.team = team
        self.car = car
        self.starting_tire = starting_tire
        self.pit_lap = pit_lap
        self.next_compound = next_compound


def _weighted_choice(weighted_values):
    """Ziehe einen Wert anhand seiner Gewichtung."""
    # Damit können wir Reifen oder Strategien leicht zufällig, aber nicht
    # komplett gleichverteilt auswählen.
    choices = [value for value, weight in weighted_values]
    weights = [weight for value, weight in weighted_values]
    return random.choices(choices, weights=weights, k=1)[0]


def _normalize_weighted_values(weighted_values):
    """Normalisiert Gewichte so, dass die Summe wieder 1.0 ergibt."""
    total_weight = sum(weight for value, weight in weighted_values)
    return [(value, weight / total_weight) for value, weight in weighted_values]


def _starting_tire_for_team(team):
    """Wählt den Startreifen für ein Team."""
    # Kleine Zufallsabweichung pro Rennen, damit sich Startstrategien nicht
    # in jedem Lauf identisch wiederholen.
    randomized_weights = []
    for compound, base_weight in BASE_STARTING_TIRE_WEIGHTS[team]:
        adjusted_weight = max(0.01, base_weight + random.uniform(-0.08, 0.08))
        randomized_weights.append((compound, adjusted_weight))

    normalized_weights = _normalize_weighted_values(randomized_weights)
    return _weighted_choice(normalized_weights)


def _next_compound_for_tire(starting_tire):
    """Bestimmt den geplanten Reifen nach dem ersten Stint."""
    return _weighted_choice(STARTING_TIRE_STRATEGIES[starting_tire]['next_compound_weights'])


def _pit_lap_for_starting_tire(team, starting_tire, total_laps):
    """Passt das Boxenfenster an den Startreifen an."""
    strategy = STARTING_TIRE_STRATEGIES[starting_tire]
    base_fraction = BASE_PIT_FRACTION_PROFILES[team]
    fraction = base_fraction * strategy['pit_fraction_factor'] + random.uniform(-0.02, 0.02)
    pit_lap = int(total_laps * fraction)
    return pit_lap


def _event_stop_compound(current_tire):
    """Wählt für einen kurzfristigen Event-Stopp einen passenden Reifen."""
    # Bei einem kurzfristigen Event-Stopp wird ein frischer Reifen gewählt.
    # Die Wahl hängt vom aktuellen Reifen ab, ist aber nicht deterministisch.
    if current_tire == 'SOFT':
        return _weighted_choice([('MEDIUM', 0.35), ('HARD', 0.65)])
    if current_tire == 'HARD':
        return _weighted_choice([('SOFT', 0.45), ('MEDIUM', 0.55)])
    return _weighted_choice([('SOFT', 0.50), ('HARD', 0.50)])


def _should_take_event_stop(opponent, safety_event_status):
    """Entscheidet, ob ein Gegner unter SC/VSC zusätzlich stoppen sollte."""
    if safety_event_status not in ('SAFETYCAR', 'VSC'):
        return False

    # Nach dem ersten geplanten Stop können weitere Stops unter Events stattfinden.
    # Maximal 3 Stops, um nicht unrealistisch zu werden.
    if opponent.car.pitstop_counter >= 3:
        return False

    tire = opponent.car.tire
    tire_age = opponent.car.tire_age

    if safety_event_status == 'SAFETYCAR':
        if tire_age < MIN_EVENT_PIT_AGE_SC[tire]:
            return False
        
    if safety_event_status == 'VSC':
        if tire_age < MIN_EVENT_PIT_AGE_VSC[tire]:
            return False

    # Event-Stop möglich nach jedem regulären/Event-Stop, solange Reifenalter passt.
    return True


def create_opponents(player_team, track, total_laps):
    """Erzeugt pro nicht gewähltem Team genau einen Gegner."""
    opponents = []

    for team in TEAM_POOL:
        if team == player_team:
            # Das eigene Team wird nicht als Gegner erzeugt.
            continue

        # Jeder Gegner bekommt ein eigenes Auto und einen eigenen Strategieplan.
        starting_tire = _starting_tire_for_team(team)
        car = Car(team, track, starting_tire)
        opponents.append(
            Opponent(
                team=team,
                car=car,
                starting_tire=starting_tire,
                pit_lap=_pit_lap_for_starting_tire(team, starting_tire, total_laps),
                next_compound=_next_compound_for_tire(starting_tire),
            )
        )

    return opponents


def advance_opponents(opponents, total_laps, safety_event_status, lap_multiplier, pitstop_multiplier):
    """Lässt alle Gegner eine Runde fahren."""
    for opponent in opponents:
        car = opponent.car

        if car.lap > total_laps:
            # Fertige Gegner werden nicht mehr weitergerechnet.
            continue

        # Erst die normale Rundenzeit berechnen, dann die Rennleitungs-Effekte anwenden.
        air_temp = st.session_state.get('air_temp', 25)
        car.predict_lap_time(air_temp=air_temp)
        car.lap_time *= lap_multiplier

        planned_stop = car.pitstop_counter == 0 and car.lap == opponent.pit_lap
        event_stop = _should_take_event_stop(opponent, safety_event_status)

        if planned_stop or event_stop:
            # Erst der normale Stopp, zusätzlich bei SC/VSC ein möglicher Bonus-Stop.
            new_tire = opponent.next_compound if planned_stop else _event_stop_compound(car.tire)
            car.box(
                new_tire,
                safety_event_status,
                pitstop_multiplier=pitstop_multiplier,
            )
        else:
            # Ansonsten fährt der Gegner einfach die Runde zu Ende.
            car.advance_lap(safety_event_status)


def build_opponent_table(opponents, total_laps):
    """Gibt die Gegnerdaten für die Tabelle zurück."""
    rows = []
    for opponent in opponents:
        # Die Tabelle soll den aktuellen Zustand der Gegner kompakt zeigen.
        last_lap_time = opponent.car.race_history[-1]['Rundenzeit'] if opponent.car.race_history else 0.0
        rows.append(
            {
                'Team': opponent.team,
                'Start-Reifen': opponent.starting_tire,
                'Aktuelle Runde': opponent.car.lap,
                'Boxenstopps': opponent.car.pitstop_counter,
                'Letzte Rundenzeit': round(last_lap_time, 2),
                'Reifen': opponent.car.tire,
                'Reifenalter': opponent.car.tire_age,
                'Geplanter Boxenlap': opponent.pit_lap,
                'Ziel-Reifenmischung': opponent.next_compound,
                'Gesamtzeit': round(opponent.car.total_time, 2),
                'Status': 'Beendet' if opponent.car.lap > total_laps else 'Läuft',
            }
        )
    return rows