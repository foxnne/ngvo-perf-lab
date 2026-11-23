# Pass 4 plan (from in-game review 2026-11-19)

## Haze follows the sun and the weather's moisture (user direction)
"the haze comes and goes with the height of the sun realistically and in certain weathers, based on moisture etc; some weathers would have a glowy hazy colorful sunset and some would have less".
- Per PERIOD values for haze (aerosol scatter/absorption), air (Rayleigh x), ozone, phase g, and sky-light settings: Dawn/Sunrise and Sunset/Dusk get more haze and warmer air than Day; Night low. Per-weather files already carry period overrides.
- A MOISTURE value per weather drives how much: by type (after-rain/showers, fog-prone, humid overcast high; crisp clear low) and by region suffix of the record (MA marsh and CO coast humid; TU tundra, SN snow, RE reach dry and crisp; PF/FF forest medium; VT volcanic hazy/dusty). Alternate records (_A, _Alt) can differ so sunsets vary day to day.
- Humid weather at low sun: haze up to ~x2 base, air x3, ozone x3, tight-ish glow: golden disc, glowing air, shafts. Dry weather: haze near base, air x2: clean orange-pink clouds, crisp distance, little glow.
- Tested ingredients (plains_west): air x3 best colour at 18:00; haze x2 brings the sun disc and halo back; air x3 + ozone x3 + haze x2 richest; sunset window only ~18:00-18:30.
- Pending tests that feed this: sunsetamb (sky light saturation 0.6 -> 1.0, weather ambient DALC 0.5 -> 0), godrays (phase g, haze x2, distance exaggeration, finer grid).
- Also for pass 4: closed decks via heavy-sky controls, storm base 350-500 m, lightning defaults from the lightning fix, Ground Fog amounts per period (now scene-drivable), burn-off.
- Midday (user, same day): haze mostly clears at the brightest part of the day "like the fog": Day period haze at or below today's base (0.2 loading) for fair types, lower still for dry regions; the morning/evening haze follows the same curve as Ground Fog burn-off (MorningAmount/MiddayAmount/EveningAmount), so mist, haze and shafts fade together and return toward evening. Humid types keep some midday haze.
