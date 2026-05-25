-- Seed data for spots_annotated table
-- 15 H3 res-11 cells in the Padova/Veneto region (center: 45.4064, 11.8768)
-- Idempotent: uses INSERT ... ON CONFLICT (h3_index) DO UPDATE

INSERT INTO spots_annotated (h3_index, rating, notes, human_score, features, created_at, updated_at)
VALUES
  -- Rating 5: Prime spots (2) - urban plazas with walls, rails, stairs
  (
    '8b1ea42db98cfff',
    5,
    'Prato della Valle - large plaza with walls, steps, and railings. Excellent parkour training area.',
    0.95,
    '{"walls": {"count": 8, "total_length_m": 45.2, "total_area_m2": 0.0}, "steps": {"count": 5, "total_length_m": 18.0, "total_area_m2": 0.0}, "rails_fences": {"count": 4, "total_length_m": 15.0, "total_area_m2": 0.0}, "playgrounds": {"count": 1, "total_length_m": 0.0, "total_area_m2": 60.0}, "good_surfaces": {"count": 5, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db981fff',
    5,
    'University area - concrete structures, multiple walls and ledges. High accessibility.',
    0.90,
    '{"walls": {"count": 6, "total_length_m": 32.0, "total_area_m2": 0.0}, "steps": {"count": 4, "total_length_m": 14.5, "total_area_m2": 0.0}, "rails_fences": {"count": 3, "total_length_m": 12.0, "total_area_m2": 0.0}, "benches_blocks": {"count": 2, "total_length_m": 5.0, "total_area_m2": 0.0}, "good_surfaces": {"count": 4, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),

  -- Rating 4: Good spots (3) - parks with multiple feature types
  (
    '8b1ea42db98efff',
    4,
    'Parco del Sacro Cuore - park with varied obstacles and playground equipment.',
    0.78,
    '{"walls": {"count": 3, "total_length_m": 15.0, "total_area_m2": 0.0}, "steps": {"count": 2, "total_length_m": 8.0, "total_area_m2": 0.0}, "rails_fences": {"count": 2, "total_length_m": 10.0, "total_area_m2": 0.0}, "playgrounds": {"count": 2, "total_length_m": 0.0, "total_area_m2": 80.0}, "good_surfaces": {"count": 2, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db988fff',
    4,
    'Riverside path - retaining walls and stairs along Bacchiglione river.',
    0.72,
    '{"walls": {"count": 5, "total_length_m": 28.0, "total_area_m2": 0.0}, "steps": {"count": 3, "total_length_m": 10.0, "total_area_m2": 0.0}, "rails_fences": {"count": 1, "total_length_m": 6.0, "total_area_m2": 0.0}, "good_surfaces": {"count": 3, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db98dfff',
    4,
    'Skatepark area - designed for action sports with ramps and rails.',
    0.80,
    '{"rails_fences": {"count": 5, "total_length_m": 20.0, "total_area_m2": 0.0}, "playgrounds": {"count": 1, "total_length_m": 0.0, "total_area_m2": 120.0}, "benches_blocks": {"count": 3, "total_length_m": 8.0, "total_area_m2": 0.0}, "good_surfaces": {"count": 4, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),

  -- Rating 3: Decent spots (4) - single feature type, moderate count
  (
    '8b1ea42db9abfff',
    3,
    'Residential area - some walls and stairs near apartment buildings.',
    0.55,
    '{"walls": {"count": 3, "total_length_m": 12.0, "total_area_m2": 0.0}, "steps": {"count": 2, "total_length_m": 6.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db9aafff',
    3,
    'Small park with playground and some benches. Limited but usable.',
    0.48,
    '{"playgrounds": {"count": 1, "total_length_m": 0.0, "total_area_m2": 45.0}, "benches_blocks": {"count": 2, "total_length_m": 4.0, "total_area_m2": 0.0}, "rails_fences": {"count": 1, "total_length_m": 5.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db985fff',
    3,
    'Train station vicinity - concrete ledges and stairs. Some access restrictions.',
    0.42,
    '{"steps": {"count": 4, "total_length_m": 15.0, "total_area_m2": 0.0}, "walls": {"count": 2, "total_length_m": 8.0, "total_area_m2": 0.0}, "private_access_penalty": {"count": 1, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db980fff',
    3,
    'School area - walls and railings. Access limited outside school hours.',
    0.50,
    '{"walls": {"count": 4, "total_length_m": 18.0, "total_area_m2": 0.0}, "rails_fences": {"count": 2, "total_length_m": 8.0, "total_area_m2": 0.0}, "private_access_penalty": {"count": 1, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),

  -- Rating 2: Limited spots (3) - few features, some access restrictions
  (
    '8b1ea42db983fff',
    2,
    'Parking lot edge - few walls and barriers. Limited variety.',
    0.28,
    '{"walls": {"count": 2, "total_length_m": 6.0, "total_area_m2": 0.0}, "parking": {"count": 1, "total_length_m": 0.0, "total_area_m2": 200.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db99dfff',
    2,
    'Industrial area - some loading docks and rails. Not ideal for training.',
    0.22,
    '{"walls": {"count": 1, "total_length_m": 4.0, "total_area_m2": 0.0}, "rails_fences": {"count": 1, "total_length_m": 3.0, "total_area_m2": 0.0}, "private_access_penalty": {"count": 1, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db98afff',
    2,
    'Residential courtyard - a few steps and low walls. Very limited.',
    0.18,
    '{"steps": {"count": 1, "total_length_m": 3.0, "total_area_m2": 0.0}, "walls": {"count": 1, "total_length_m": 2.5, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),

  -- Rating 1: Poor spots (2) - minimal features
  (
    '8b1ea42db98bfff',
    1,
    'Open square with a single bench. Almost no parkour value.',
    0.10,
    '{"benches_blocks": {"count": 1, "total_length_m": 2.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),
  (
    '8b1ea42db989fff',
    1,
    'Street corner with a low wall. Minimal training potential.',
    0.08,
    '{"walls": {"count": 1, "total_length_m": 1.5, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  ),

  -- Rating 0: No parkour value (1) - open field only
  (
    '8b1ea42db832fff',
    0,
    'Open grass field - no structures or features for parkour.',
    0.02,
    '{"good_surfaces": {"count": 1, "total_length_m": 0.0, "total_area_m2": 0.0}}',
    NOW(),
    NOW()
  )

ON CONFLICT (h3_index) DO UPDATE SET
  rating = EXCLUDED.rating,
  notes = EXCLUDED.notes,
  human_score = EXCLUDED.human_score,
  features = EXCLUDED.features,
  updated_at = NOW();
