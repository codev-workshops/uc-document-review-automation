# Fuzzy-matching A/B accuracy report

Labeled rows: 66 (name=36, address=30; positives name=18, address=17)

Dataset: tests/fixtures/labeled_pairs.json. Regenerate with `python scripts/ab_accuracy_harness.py`.

## Summary (configured threshold per algorithm)

| field type | algorithm | threshold | precision | recall | F1 | TP | FP | TN | FN |
|---|---|---|---|---|---|---|---|---|---|
| name | jaccard | 0.85 | 1.000 | 1.000 | 1.000 | 18 | 0 | 18 | 0 |
| address | jaccard | 0.80 | 1.000 | 1.000 | 1.000 | 17 | 0 | 13 | 0 |
| name | levenshtein | 0.97 | 1.000 | 1.000 | 1.000 | 18 | 0 | 18 | 0 |
| address | levenshtein | 0.98 | 1.000 | 1.000 | 1.000 | 17 | 0 | 13 | 0 |

## Same algorithms at the legacy Jaccard-tuned thresholds

Shows why the cutoff must travel with the algorithm.

| field type | algorithm | legacy threshold | precision | recall | F1 | FP | FN |
|---|---|---|---|---|---|---|---|
| name | jaccard | 0.85 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| address | jaccard | 0.80 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| name | levenshtein | 0.85 | 0.720 | 1.000 | 0.837 | 7 | 0 |
| address | levenshtein | 0.80 | 0.708 | 1.000 | 0.829 | 7 | 0 |

## Threshold sweep - best cutoff per algorithm

| field type | algorithm | best threshold | at best | configured | at configured |
|---|---|---|---|---|---|
| name | jaccard | 0.84 | P=1.000 R=1.000 F1=1.000 (TP=18 FP=0 TN=18 FN=0) | 0.85 | P=1.000 R=1.000 F1=1.000 (TP=18 FP=0 TN=18 FN=0) |
| address | jaccard | 0.84 | P=1.000 R=1.000 F1=1.000 (TP=17 FP=0 TN=13 FN=0) | 0.80 | P=1.000 R=1.000 F1=1.000 (TP=17 FP=0 TN=13 FN=0) |
| name | levenshtein | 0.97 | P=1.000 R=1.000 F1=1.000 (TP=18 FP=0 TN=18 FN=0) | 0.97 | P=1.000 R=1.000 F1=1.000 (TP=18 FP=0 TN=18 FN=0) |
| address | levenshtein | 0.98 | P=1.000 R=1.000 F1=1.000 (TP=17 FP=0 TN=13 FN=0) | 0.98 | P=1.000 R=1.000 F1=1.000 (TP=17 FP=0 TN=13 FN=0) |

### name / jaccard

Confusion matrix at configured threshold 0.85:

|            | predicted match | predicted mismatch |
|---|---|---|
| actual match | 18 | 0 |
| actual mismatch | 0 | 18 |

Threshold sweep (every 0.05):

| threshold | precision | recall | F1 | FP | FN |
|---|---|---|---|---|---|
| 0.50 | 0.900 | 1.000 | 0.947 | 2 | 0 |
| 0.55 | 0.900 | 1.000 | 0.947 | 2 | 0 |
| 0.60 | 0.900 | 1.000 | 0.947 | 2 | 0 |
| 0.65 | 0.900 | 1.000 | 0.947 | 2 | 0 |
| 0.70 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.75 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.80 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.85 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.90 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.95 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 1.00 | 1.000 | 1.000 | 1.000 | 0 | 0 |

### address / jaccard

Confusion matrix at configured threshold 0.80:

|            | predicted match | predicted mismatch |
|---|---|---|
| actual match | 17 | 0 |
| actual mismatch | 0 | 13 |

Threshold sweep (every 0.05):

| threshold | precision | recall | F1 | FP | FN |
|---|---|---|---|---|---|
| 0.50 | 0.630 | 1.000 | 0.773 | 10 | 0 |
| 0.55 | 0.850 | 1.000 | 0.919 | 3 | 0 |
| 0.60 | 0.850 | 1.000 | 0.919 | 3 | 0 |
| 0.65 | 0.895 | 1.000 | 0.944 | 2 | 0 |
| 0.70 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.75 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.80 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.85 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.90 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 0.95 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 1.00 | 1.000 | 1.000 | 1.000 | 0 | 0 |

### name / levenshtein

Confusion matrix at configured threshold 0.97:

|            | predicted match | predicted mismatch |
|---|---|---|
| actual match | 18 | 0 |
| actual mismatch | 0 | 18 |

Threshold sweep (every 0.05):

| threshold | precision | recall | F1 | FP | FN |
|---|---|---|---|---|---|
| 0.50 | 0.529 | 1.000 | 0.692 | 16 | 0 |
| 0.55 | 0.545 | 1.000 | 0.706 | 15 | 0 |
| 0.60 | 0.562 | 1.000 | 0.720 | 14 | 0 |
| 0.65 | 0.581 | 1.000 | 0.735 | 13 | 0 |
| 0.70 | 0.600 | 1.000 | 0.750 | 12 | 0 |
| 0.75 | 0.621 | 1.000 | 0.766 | 11 | 0 |
| 0.80 | 0.643 | 1.000 | 0.783 | 10 | 0 |
| 0.85 | 0.720 | 1.000 | 0.837 | 7 | 0 |
| 0.90 | 0.750 | 1.000 | 0.857 | 6 | 0 |
| 0.95 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 1.00 | 1.000 | 1.000 | 1.000 | 0 | 0 |

### address / levenshtein

Confusion matrix at configured threshold 0.98:

|            | predicted match | predicted mismatch |
|---|---|---|
| actual match | 17 | 0 |
| actual mismatch | 0 | 13 |

Threshold sweep (every 0.05):

| threshold | precision | recall | F1 | FP | FN |
|---|---|---|---|---|---|
| 0.50 | 0.607 | 1.000 | 0.756 | 11 | 0 |
| 0.55 | 0.607 | 1.000 | 0.756 | 11 | 0 |
| 0.60 | 0.607 | 1.000 | 0.756 | 11 | 0 |
| 0.65 | 0.630 | 1.000 | 0.773 | 10 | 0 |
| 0.70 | 0.654 | 1.000 | 0.791 | 9 | 0 |
| 0.75 | 0.680 | 1.000 | 0.809 | 8 | 0 |
| 0.80 | 0.708 | 1.000 | 0.829 | 7 | 0 |
| 0.85 | 0.739 | 1.000 | 0.850 | 6 | 0 |
| 0.90 | 0.773 | 1.000 | 0.872 | 5 | 0 |
| 0.95 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| 1.00 | 1.000 | 1.000 | 1.000 | 0 | 0 |

## All scores

### name

| document value | record value | expected | jaccard | levenshtein |
|---|---|---|---|---|
| John Smith | John Smith | match | 1.000 | 1.000 |
| JOHN SMITH | john smith | match | 1.000 | 1.000 |
| Mr. John Smith | John Smith | match | 1.000 | 1.000 |
| Smith John | John Smith | match | 1.000 | 1.000 |
| John Smith | Jane Doe | mismatch | 0.000 | 0.200 |
|  |  | match | 1.000 | 1.000 |
| John |  | mismatch | 0.000 | 0.000 |
| John Smith | john smith | match | 1.000 | 1.000 |
| Jon Smith | John Smith | mismatch | 0.333 | 0.900 |
| Dr. Jane Doe Jr. | Jane Doe | match | 1.000 | 1.000 |
| Robert A. Lee | Robert A Lee | match | 1.000 | 1.000 |
| Jean-Luc Picard | JEAN-LUC PICARD | match | 1.000 | 1.000 |
| Conor O’Brien | Conor O'Brien | match | 1.000 | 1.000 |
| José Muñoz | JOSÉ MUÑOZ | match | 1.000 | 1.000 |
| Maria Garcia Lopez | Maria Garcia Lopez | match | 1.000 | 1.000 |
| Lopez Maria Garcia | Maria Garcia Lopez | match | 1.000 | 1.000 |
| Henry Ford II | Henry Ford | match | 1.000 | 1.000 |
| Priya Natarajan | Priya Natarajan | match | 1.000 | 1.000 |
| Michael Smith | John Smith | mismatch | 0.333 | 0.538 |
| John Smith | John Smithson | mismatch | 0.333 | 0.769 |
| Ann Lee | Anna Li | mismatch | 0.000 | 0.571 |
| Robert Lee | Robert A Lee | mismatch | 0.667 | 0.833 |
| Maria Gracia | Maria Garcia | mismatch | 0.333 | 0.833 |
| Jonathan Harris | Jonathan Haris | mismatch | 0.333 | 0.933 |
| Jose Munoz | José Muñoz | mismatch | 0.000 | 0.800 |
| Jean Luc Picard | Jean-Luc Picard | mismatch | 0.250 | 0.933 |
| William Brown | Wiliam Brown | mismatch | 0.333 | 0.923 |
| David Kim | Daniel Kim | mismatch | 0.333 | 0.700 |
| Sara Cohen | Sarah Cohen | mismatch | 0.333 | 0.909 |
| Thomas Anderson | Thomas Andersen | mismatch | 0.333 | 0.933 |
| Chris Evans | Christopher Evans | mismatch | 0.333 | 0.647 |
| Wei Chen | Wei Cheng | mismatch | 0.333 | 0.889 |
| Amy Wong Tan | Amy Wong | mismatch | 0.667 | 0.667 |
| Peter Parker | Parker Peter | match | 1.000 | 1.000 |
| Владимир Петров | владимир петров | match | 1.000 | 1.000 |
| Mrs. Alice Johnson | Ms Alice Johnson | match | 1.000 | 1.000 |

### address

| document value | record value | expected | jaccard | levenshtein |
|---|---|---|---|---|
| 123 Main Street | 123 Main Street | match | 1.000 | 1.000 |
| 123 Main Street | 123 Main St | match | 1.000 | 1.000 |
| 123 MAIN ST | 123 main st | match | 1.000 | 1.000 |
| 456 North Oak Avenue | 456 N Oak Ave | match | 1.000 | 1.000 |
| 123 Main St | 789 Elm Blvd | mismatch | 0.000 | 0.083 |
| 456 N. Oak Ave., Apt. 3 | 456 N Oak Ave Apt 3 | match | 1.000 | 1.000 |
| 100 Commerce Drive Suite 200 | 100 Commerce Dr Ste 200 | match | 1.000 | 1.000 |
| 789 Elm Boulevard | 789 Elm Blvd | match | 1.000 | 1.000 |
| 12 Court Place | 12 Ct Pl | match | 1.000 | 1.000 |
| 200 Tech Building 4 | 200 Tech Bldg 4 | match | 1.000 | 1.000 |
| 100  Commerce   Dr | 100 Commerce Dr | match | 1.000 | 1.000 |
| 55 Lake Circle, Springfield | 55 Lake Cir Springfield | match | 1.000 | 1.000 |
| 9 West Lane #2 | 9 W Ln 2 | match | 1.000 | 1.000 |
| 34 South River Road | 34 S River Rd | match | 1.000 | 1.000 |
| 100 Commerce Dr | 101 Commerce Dr | mismatch | 0.500 | 0.933 |
| 123 Main St | 132 Main St | mismatch | 0.500 | 0.818 |
| 55 Lake Cir Unit B | 55 Lake Cir | mismatch | 0.600 | 0.611 |
| 100 Commerce Dr | 900 Commerce Dr Suite 1 | mismatch | 0.333 | 0.667 |
| 123 Main St | 123 Maine St | mismatch | 0.500 | 0.917 |
| 10 Oak Ave | 10 Oak Ct | mismatch | 0.500 | 0.700 |
| 77 East Street | 77 West Street | mismatch | 0.500 | 0.857 |
| 8 Pine Court Apt 4 | 8 Pine Ct Apt 5 | mismatch | 0.667 | 0.933 |
| 1 Ford Road | 1 Ford Rd | match | 1.000 | 1.000 |
| 500 5th Avenue Apt 12B | 500 5th Ave Apt 12B | match | 1.000 | 1.000 |
| 500 5th Ave Apt 12B | 500 5th Ave Apt 12C | mismatch | 0.667 | 0.947 |
| 2200 Sunset Blvd | 220 Sunset Blvd | mismatch | 0.500 | 0.938 |
| 45 Elm Street North | 45 Elm St N | match | 1.000 | 1.000 |
| 45 Elm St | 54 Elm St | mismatch | 0.500 | 0.778 |
|  |  | match | 1.000 | 1.000 |
| 123 Main St |  | mismatch | 0.000 | 0.000 |
