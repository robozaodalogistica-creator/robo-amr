# NOTICE

This product includes software developed by third parties. See
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) for the complete list
of licenses.

---

## Attribution: rbot

Portions of this codebase under `src/rbot/` are derived from the **rbot**
project by **Robolabs AI (RLXAI ROBOLABSAI PRIVATE LIMITED)**,
distributed under the Apache License, Version 2.0.

- Upstream source: https://github.com/rlxai/rbot
- Imported at commit: `b8095e7d6b91faa04499a234b7baaacc2d831f20`
- Original copyright: © 2026 Robolabs AI

### What we adopted

The entire ROS 2 workspace tree was imported as our base platform:

- `bringup/`, `control/`, `localization/`, `mapping/`, `navigation/`,
  `perception/`, `robot/`, `simulation/`, `utils/`

This gives us a working Gazebo + Nav2 + EKF/AMCL + SLAM Toolbox stack on
ROS 2 Jazzy as a starting point.

### What we modified / why

Baseado no rbot original, modificamos o código para uso em **AMR de pallet
para galpão robô-only** (sem humanos circulando, ambiente estruturado e
controlado, foco em movimentação de paletes).

Modifications introduced by this project (and any future ones) include,
without limitation:

- Mission and task-allocation logic specific to pallet handling.
- Fleet coordination for multi-robot pallet flows.
- Sensor and safety configurations tuned for a robot-only warehouse
  (different risk profile from the upstream's mixed-environment defaults).
- Integration with our planning, perception, and orchestration layers.

We retain the original credits and copyright notices in every file we
inherit. Files we modify will carry a change notice at the top, per
Apache 2.0 §4(b). Files we add from scratch are copyright of this
project's authors and are made available under the same Apache 2.0
license unless stated otherwise.

### Trademarks

"rbot" and "Robolabs AI" are referenced solely for attribution under
Apache 2.0 §4. This project is **not** affiliated with, endorsed by, or
sponsored by Robolabs AI. Any trademarks remain the property of their
respective owners.
