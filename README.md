# Drone Pricing Model

A Python rebuild of the hx drone exposure-rating spreadsheet. It prices hull and third-party liability (TPL) cover for a fleet of drones and detachable cameras, and adds the two suggested extensions and handling for missing data. It uses the standard library only.

## Quick start

Requires Python 3.10+.

```bash
python3 main.py            # price the example fleet and print the full result
python3 -m unittest        # run the tests
```

```python
from drone_pricing.data_structure import Submission
from drone_pricing.pricing import price_submission

submission = price_submission(Submission.from_dict(data), seed=1)  # seed is optional: it makes tie-breaks reproducible
submission.to_dict()   # every input, intermediate value and output
submission.warnings    # anything that could not be priced, and why
```

On the example data, the model reproduces the spreadsheet: net £4,042.11 and gross £5,774.45. After the extensions, the premiums are net £3,240.11 and gross £4,628.74.

## Project structure

| Path | Contents |
|---|---|
| `main.py` | Runs the example and prints the result |
| `drone_pricing/data_structure.py` | Dataclasses `Submission`, `Drone`, `Camera` and `Premiums`: input checks and the output structure |
| `drone_pricing/pricing.py` | Pricing steps. Each function mirrors a spreadsheet calculation, and its docstring names the cells (e.g. `Model!L:O`) so values can be checked against the workbook |
| `drone_pricing/parameters.py` | Rates, weight bands, Riebesell parameters and the extension fees (the spreadsheet's Parameters sheet) |
| `drone_pricing/utils.py` | Riebesell curve, gross-up and random tie-break ranking |
| `drone_pricing/example_data.py` | The spreadsheet's example fleet |
| `tests/` | Unit tests (`unittest`) |
| `initial_documents/` | The original brief, spreadsheet and starter code |

## Inputs and outputs

The input is a dict in the starter code's layout. Only the inputs are required. Output placeholders are optional, and any values in them are ignored and recalculated.

| Level | Inputs |
|---|---|
| Submission | `insured`, `underwriter`, `broker`, `brokerage` $b$ ($0 \le b < 1$), `max_drones_in_air` $n$ (integer $\ge 0$), `drones`, `detachable_cameras` |
| Drone | `serial_number`, `value`, `weight` (band label such as `"0 - 5kg"`, or kg), `has_detachable_camera`, `tpl_limit`, `tpl_excess` |
| Camera | `serial_number`, `value` |

The outputs are written into the same structure, so printing it shows everything:

- **Drone:** `weight_category`, `hull_base_rate`, `hull_weight_adjustment`, `hull_final_rate`, `hull_premium`, `tpl_base_rate`, `tpl_base_layer_premium`, `tpl_ilf` and `tpl_layer_premium`. From the extension: `rank`, `charged_full_rate`, `final_hull_premium` and `final_tpl_premium`.
- **Camera:** `hull_rate` and `hull_premium`. From the extension: `rank`, `charged_full_rate` and `final_hull_premium`.
- **Submission:** `net_prem` and `gross_prem` (the spreadsheet's summary), `net_prem_after_extensions`, `gross_prem_after_extensions`, and `warnings`.

Extension results are stored in separate fields, so the spreadsheet figures stay visible and can be checked against the workbook.

## Current pricing model

The model formulas for hull and TPL cover for drones and camera attachments are as follows.

### Hull premium

Let $i$ be a drone in fleet $j$. The **gross hull premium** (GHP) for drone $i$ is:

$$
\text{GHP}(i) = 0.06 \times \text{WeightAdj}(i) \times \text{Value}(i)
$$

where $\text{Value}(i)$ is the value of drone $i$, and $\text{WeightAdj}(i)$ is the weight adjustment factor:

$$
\text{WeightAdj}(i) =
\begin{cases}
1.0 & \text{if drone } i \text{ weighs } 0\text{–}5\text{ kg} \cr
1.2 & \text{if drone } i \text{ weighs } 5\text{–}10\text{ kg} \cr
1.6 & \text{if drone } i \text{ weighs } 10\text{–}20\text{ kg} \cr
2.5 & \text{if drone } i \text{ weighs } > 20\text{ kg}
\end{cases}
$$

> **Note:** $\text{GHP}(i)$ is `NA` if $\text{Value}(i)$ is missing or zero.

### TPL premium

Each drone buys a TPL layer of $\text{Limit}(i)$ in excess of $\text{Excess}(i)$. The TPL premium is priced in two steps.

First, the **base layer premium** (BLP) is the premium for the base limit of £1,000,000 with no excess:

$$
\text{BLP}(i) = 0.02 \times \text{Value}(i)
$$

(Unlike hull, no weight adjustment is applied.)

Second, the base layer premium is scaled to the drone's actual layer by an **increased limit factor** (ILF) taken from a Riebesell curve $R(\cdot)$ (see [The Riebesell curve](#the-riebesell-curve) below):

$$
\text{ILF}(i) = R\big(\text{Limit}(i) + \text{Excess}(i)\big) - R\big(\text{Excess}(i)\big)
$$

The **gross liability premium** (GLP) for drone $i$ is then:

$$
\text{GLP}(i) = \text{BLP}(i) \times \text{ILF}(i)
$$

> **Note:** $\text{GLP}(i)$ is `NA` if $\text{Value}(i)$ is missing or zero.

### Detachable cameras

Let $k$ be a detachable camera, and let $C$ be the set of drones that have a detachable camera and $\text{Value}(i) > 0$. Every camera gets the same hull rate: the highest final hull rate among the drones in $C$:

$$
\text{CamRate} = \max_{i \in C} \big( 0.06 \times \text{WeightAdj}(i) \big)
$$

Since we don't know which drone a camera will be mounted on, it is priced as if it were on the riskiest eligible drone. The camera hull premium (CHP) is:

$$
\text{CHP}(k) = \text{CamRate} \times \text{Value}(k)
$$

> **Note:** $\text{CHP}(k)$ is `NA` if $\text{Value}(k)$ is missing or zero. If no drone has a detachable camera, the spreadsheet gives $\text{CamRate} = 0$ (what Excel's `MAXIFS` returns when nothing matches). The Python model instead removes the cameras with a warning (see [My improvements](#my-improvements)).

### Premium summary

The per-item premiums are summed across the fleet:

$$
\text{Hull} = \sum_i \text{GHP}(i), \qquad
\text{TPL} = \sum_i \text{GLP}(i), \qquad
\text{Camera} = \sum_k \text{CHP}(k)
$$

and the total is $\text{Hull} + \text{TPL} + \text{Camera}$ (`NA` items are skipped). The spreadsheet labels these sums **net** and grosses each one up for brokerage $b$ (30% in the example):

$$
\text{Gross} = \frac{\text{Net}}{1 - b}
$$

### Parameters

| Parameter | Value |
|---|---|
| Hull base rate | 6% |
| TPL base rate | 2% |
| Riebesell base limit $B$ | £1,000,000 |
| Riebesell $z$ | 0.2 |
| Weight adjustments | see $\text{WeightAdj}$ above |

### The Riebesell curve

A **Riebesell curve** is an increased-limit-factor curve used in liability pricing, mostly in European markets. It rests on one assumption:

> Every time the limit doubles, the premium goes up by a fixed factor of $(1 + z)$.

With $z = 0.2$, going from a £1m limit to £2m costs 20% more, going to £4m costs another 20% on top of that, and so on. Each extra £1 of cover is worth less than the one before, because large losses are rarer than small ones.

#### Formula

For a base limit $B$ and parameter $z$, the factor for total cover up to $x$ is:

$$
R(x) = \left(\frac{x}{B}\right)^{\log_2(1 + z)}
$$

The workbook implements this as a VBA function (`Module1`):

```vba
Function Riebesell(riebesell_base_limit As Double, riebesell_z As Double, x As Double) As Double
    Riebesell = (x / riebesell_base_limit) ^ Application.Log(1 + riebesell_z, 2)
End Function
```

Key properties:

- $R(B) = 1$: the base limit is priced at exactly the base layer premium.
- $R(2x) = (1 + z) R(x)$: this is the doubling rule. Because $(2x/B)^{\log_2(1+z)} = 2^{\log_2(1+z)} \cdot (x/B)^{\log_2(1+z)} = (1+z) R(x)$.
- $R(0) = 0$ when $z > 0$, so a layer with no excess has $\text{ILF} = R(\text{Limit})$.
- For $0 < z < 1$ the exponent is between 0 and 1, so the curve is increasing and concave. Higher layers cost less per £ of cover.

#### Pricing a layer

A layer "$L$ xs $E$" pays losses between $E$ and $E + L$, so its factor is the difference between the curve at the top and the bottom of the layer:

$$
\text{ILF} = R(E + L) - R(E)
$$

## Extensions

### 1. More drones than can fly at once ($N > n$)

Customers may have a large fleet of $N$ drones but warrant that at most $n$ will fly at any one time (`max_drones_in_air`). The $n$ drones with the highest premiums are charged the full rate, and every other drone is charged a fixed £150.

**Step 1.** Calculate $\text{GHP}(i)$ and $\text{GLP}(i)$ for each drone as above, and combine them:

$$
P(i) = \text{GHP}(i) + \text{GLP}(i)
$$

**Step 2.** Rank the drones with $\text{Value}(i) > 0$ by $P(i)$, highest first. Let $r(i)$ be drone $i$'s rank, with ties broken at random (pass a seed to make the result reproducible).

**Step 3.** Keep the full premium for the top $n$ drones and charge £150 for the rest:

$$
P^{\ast}(i) =
\begin{cases}
P(i) & \text{if } r(i) \le n \cr
150 & \text{if } r(i) > n
\end{cases}
$$

**Step 4.** So that the premium summary can still show hull and TPL separately, split the £150 between them in the same proportions as the drone's full premium:

$$
\text{GHP}^{\ast}(i) = P^{\ast}(i) \times \frac{\text{GHP}(i)}{P(i)}, \qquad
\text{GLP}^{\ast}(i) = P^{\ast}(i) \times \frac{\text{GLP}(i)}{P(i)}
$$

If $N \le n$, every drone ranks in the top $n$, so nothing changes.

### 2. More cameras than can fly at once

Most of the risk to cameras comes when they're in the air, and a camera can only be in the air while it is mounted on a flying drone. So at most

$$
m = \min\big(n, \lvert C \rvert\big)
$$

cameras can be airborne at once, where $\lvert C \rvert$ is the number of drones that have a detachable camera and a non-zero value (the set $C$ defined under [Detachable cameras](#detachable-cameras)). The $m$ most valuable cameras are charged the full rate, and every other camera is charged a fixed £50.

**Step 1.** Rank the cameras with $\text{Value}(k) > 0$ by value, highest first. Let $s(k)$ be camera $k$'s rank, with ties broken at random.

**Step 2.** Every camera has the same rate, so ranking by value gives the same order as ranking by premium. Charge the full premium for the top $m$ cameras and £50 for the rest:

$$
\text{CHP}^{\ast}(k) =
\begin{cases}
\text{CamRate} \times \text{Value}(k) & \text{if } s(k) \le m \cr
50 & \text{if } s(k) > m
\end{cases}
$$

If there are $m$ or fewer cameras, nothing changes.

## Assumptions

- **Example data:** the starter `.py` was missing the `tpl_limit` and `tpl_excess` values (a syntax error), and it named the third drone `AAA-123`. The values here are taken from the spreadsheet instead: `CCC-333`, and limits/excesses of 1m/0, 4m/1m and 5m/5m.
- **Cameras charged the full rate:** the brief says "the n cameras", but a camera can only fly on a flying drone that takes a camera, so $m = \min(n, \lvert C \rvert)$.
- **Ties** in the extension rankings are broken at random rather than by serial number.

## My improvements

1. **Exact weights:** `weight` can be a band label or an exact weight in kg, which is mapped to its band and shown in `weight_category`. Each band includes its upper limit: 5 kg is in "0 - 5kg" and 20 kg is in "10 - 20kg", since the top band is "> 20kg".
2. **Partial pricing with warnings:** if a drone or camera has missing or invalid information (e.g. a negative value, an unknown weight label, a limit of 0), only that item is removed. The rest of the fleet is priced, and `warnings` lists what was removed and why. For example: *"Fleet has been priced with camera ZZZ-999 removed because: value is missing"*. Submission-level inputs (`brokerage`, `max_drones_in_air`) still raise an error, because nothing can be priced without them.
3. **Only the inputs are needed:** output placeholders don't need to be supplied. The model creates and fills them.
4. **Missing `has_detachable_camera`:** this flag affects both the drone and the cameras, so:
   - If there are no cameras to price, the flag isn't needed and the drone is priced.
   - If there are cameras, the drone is still priced when its flag can't change the camera pricing. This requires both (a) its hull rate is at or below $\text{CamRate}$, so the rate is unchanged, and (b) at least $n$ drones are known to take a camera, so $m$ is unchanged. A warning notes that the flag was missing but didn't affect pricing.
   - Otherwise, the drone is removed and everything else, including the cameras, is priced. An alternative would be to keep the drone and remove all the cameras instead.
5. **No drone takes a camera:** if the fleet has cameras but no drone is known to take one (every flag is `False` or missing), the cameras are removed with a warning and the drones are still priced. Missing flags no longer matter in this case. The spreadsheet would give these cameras a £0 premium, which is misleading if you only look at the total.

The tests check that the model matches the spreadsheet's values, and cover the Riebesell curve properties, the input checks, both extensions, random tie-breaks and missing data.

## Limitations

1. **Ties at the cut-off:** if drones tie on premium at rank $n$ (or cameras tie on value at rank $m$), which one is charged the full rate is random. The overall total is unaffected, but item-level premiums, and for drones the hull/TPL split, can change between runs unless a seed is passed.
2. **Removed items are excluded from the total:** the quoted premium is understated until the missing information is supplied. The warnings make this visible.
3. **Gross or net:** the spreadsheet's Parameters sheet labels the base rates "Gross", but the premium summary treats their sums as net and grosses them up for brokerage. This is worth confirming.

## Recommendations

1. **Cap at the full premium:** as written, a drone whose full premium is under £150 would be charged more for not flying. I'd suggest charging whichever is lower, the full premium or £150 (and likewise £50 for cameras).
