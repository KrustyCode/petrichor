SR = 44100        # sample rate (Hz)
BLOCK = 22_500      # frames per callback == len(self.out) <-- bigger block let the threads had more room to breath
CHANNELS = 1
QUEUE_DEPTH = 8

ORGANIC = "organic"   # re-rendered (new variation) whenever exhausted
STEADY = "steady"     # looped; re-rendered only on param change


PRESETS = {
    "savannah":            {"rain":0,   "wind":0.5, "bird":0.3, "cricket":0.2, "beetle":0,   "frog":0,   "woodpecker":0,   "savannah grass":0.7, "cicada":0.4, "distant call":0.5, "thunder strike":0, "river": 0},
    "rainforest":          {"rain":0.6, "wind":0.2, "bird":0.6, "cricket":0.5, "beetle":0.2, "frog":0.5, "woodpecker":0.4, "savannah grass":0,   "cicada":0.6, "distant call":0.2, "thunder strike":0, "river": 0.4},
    "thunderstorm":        {"rain":0.8, "wind":0.7, "bird":0,   "cricket":0,   "beetle":0,   "frog":0,   "woodpecker":0,   "savannah grass":0,   "cicada":0,   "distant call":0,   "thunder strike":0.6, "river": 0},
    "wetland_marsh":       {"rain":0.2, "wind":0.1, "bird":0.3, "cricket":0.6, "beetle":0,   "frog":0.8, "woodpecker":0,   "savannah grass":0,   "cicada":0,   "distant call":0,   "thunder strike":0, "river": 0.2},
    "forest_night":        {"rain":0,   "wind":0.3, "bird":0,   "cricket":0.7, "beetle":0,   "frog":0.5, "woodpecker":0,   "savannah grass":0,   "cicada":0,   "distant call":0.4, "thunder strike":0, "river": 0},
    "summer_meadow_day":   {"rain":0,   "wind":0.4, "bird":0.4, "cricket":0.1, "beetle":0.3, "frog":0,   "woodpecker":0,   "savannah grass":0.5, "cicada":0.6, "distant call":0,   "thunder strike":0, "river": 0},
    "jungle_morning":      {"rain":0.1, "wind":0.1, "bird":0.7, "cricket":0.3, "beetle":0,   "frog":0,   "woodpecker":0.6, "savannah grass":0,   "cicada":0.5, "distant call":0,   "thunder strike":0, "river": 0.3},
    "spring_woodland":     {"rain":0,   "wind":0.3, "bird":0.6, "cricket":0.3, "beetle":0,   "frog":0,   "woodpecker":0.5, "savannah grass":0,   "cicada":0,   "distant call":0,   "thunder strike":0, "river": 0.2},
    "storm_rolling_in":    {"rain":0.3, "wind":0.6, "bird":0,   "cricket":0,   "beetle":0,   "frog":0,   "woodpecker":0,   "savannah grass":0.2, "cicada":0.2, "distant call":0.3, "thunder strike":0.2, "river": 0},
    "african_plains_night":{"rain":0,   "wind":0.5, "bird":0,   "cricket":0.5, "beetle":0,   "frog":0,   "woodpecker":0,   "savannah grass":0.6, "cicada":0,   "distant call":0.6, "thunder strike":0, "river": 0},
    "pond_at_dusk":        {"rain":0,   "wind":0.2, "bird":0.2, "cricket":0.5, "beetle":0,   "frog":0.7, "woodpecker":0,   "savannah grass":0,   "cicada":0.1, "distant call":0,   "thunder strike":0, "river": 0.3},
    "riverside":           {"rain":0,   "wind":0.3, "bird":0.4, "cricket":0.2, "beetle":0.4, "frog":0.2, "woodpecker":0.2, "savannah grass":0,   "cicada":0.2, "distant call":0,   "thunder strike":0, "river": 0.8},
}
