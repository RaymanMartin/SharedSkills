# Qualcomm Bluetooth QDID / DN Reference

> Source: KBA-240702233705_REV_6 — CNSS BT Mobile Android BT DN/QDID List
> Primary PDF: `/home/quectel/Documents/Bluetooth/Bluetooth/KBA-240702233705_REV_6__CNSS_BT_Mobile_Android_BT_DN_QDID_List_and_corresponding_Q_A.pdf`
> Also check for newer revisions in the same folder.

---

## Key Concepts

- **BT Version** = min(Host version, Controller version)
- **Controller** = BT firmware on the WCN SoC (depends on WCN chip ID)
- **Host** = BT stack running on the application CPU (depends on Android OS version)
- **QDID** (older) / **DN** (new since July 2024) — use either interchangeably for certification reference

---

## 2.1 Controller QDID/DN (by WCN Chip)

| WCN Chip | Declaration ID | QDID/DN | BT Spec Ver | FW Build / Note |
|----------|---------------|---------|-------------|-----------------|
| WCN788x / WCN786x | Q369405 | — | V6.0 | BTFW.GANGES.2.0.1, BTFW.BRAHMA.2.0.1 |
| WCN788x / WCN786x | Q308763 | — | V6.0 | BTFW.GANGES.2.0.0, BTFW.BRAHMA.2.0.0 |
| WCN7750 | Q344169 | — | V6.0 | BTFW.ORNE.1.0.0 |
| WCN788x / WCN786x | D067084 | 242271 | V5.4 | RF/PHY |
| WCN788x / WCN786x | D065244 | 244214 | V5.4 | BTFW.GANGES.2.0.0 |
| WCN7850 / WCN7851 | Q348322 | — | V6.0 | BTFW.HAMILTON.2.0.3 |
| WCN7850 / WCN7851 | D060636 | 205573 | V5.4 | BTFW.HAMILTON.2.0.1 |
| WCN7850 / WCN7851 | D058477 | 194050 | V5.3 | RF & RF PHY |
| WCN7850 / WCN7851 | D058476 | 194301 | V5.3 | BTFW.HAMILTON.2.0.0 |
| WCN6855 / WCN6856 | D054625 | 179073 | V5.3 | BTFW.HSP.2.1.0 |
| WCN6855 / WCN6856 | D054623 | 176206 | V5.2 | BTFW.HSP.2.1.0 |
| WCN6855 / WCN6856 | D049737 | 160294 | V5.2 | BTFW.HSP.2.0.0 |
| WCN6850 / WCN6851 | D049735 | 151965 | V5.2 | BTFM.HSP.1.0.0 |
| WCN6850 / WCN6851 | D051872 | 164097 | V5.2 | BTFM.HSP.1.0.2 |
| WCN685x | D049736 | 152120 | V5.2 | RF & RF PHY |
| WCN6755 | D065241 | 219467 | V5.4 | BTFW.MOSELLE.1.2.0 |
| WCN6750 | Q330089 | — | V5.4 | BTFW.MOSELLE.1.1.3 |
| WCN6750 | D054628 | 185085 | V5.2 | BTFW.MOSELLE.1.1.0 |
| WCN6750 | D053613 | 168072 | V5.2 | BTFW.MOSELLE.1.1.0/1.1.1 |
| WCN6750 | D054621 | 172466 | V5.2 | RF & RF PHY |
| WCN6740 | D051869 | 164611 | V5.2 | BTFW.HSP.2.0.0 |
| WCN6450 | Q363448 | — | V6.0 | BTFW.EVROS.2.0 |
| QCA639x | D047380 | 143986 | V5.2 | BTFM.HST.2.0.0 |
| QCA639x | D043256 | 138012 | V5.1 | BTFM.HST.2.0.0 |
| WCN3998-1 | D047381 | 144597 | V5.2 | BTFM.CHE.3.2.1 |
| WCN3998-1 / WCN3991 | D047379 | 142659 | V5.1 | BTFM.CHE.3.2.0 |
| WCN39x8 / WCN3990 | D043254 | 133994 | V5.1 | BTFM.CHE.2.1.5/2.1.6 |
| WCN3998-0 | D040524 | 119326 | V5.0 | BTFM.CHE.2.1.4 |
| WCN3990 | D039228 | 116819 | V5.0 | BTFM.CHE.2.1.4 |
| WCN3990 | D033529 | 96248 | V5.0 | BTFM.CHE.2.1.3 |
| WCN3990 | D033273 | 91359 | V5.0 | BTFM.CHE.2.1.1 |
| WCN3990 | D033517 | 92155 | V5.0 | RF & RF PHY |
| WCN3980 | D033518 | 95175 | V5.0 | BTFM.CHE.2.1.1 |
| WCN3950 | Q380658 | — | V4.2 | BTFM.CMC.1.3.0 |
| WCN3950 | D054622 | 175251 | V5.0 | BTFM.CMC.1.3.0 |
| WCN3950 | D040527 | 133390 | V5.0 | BTFM.CMC.1.2.0 |
| QCA61x4A | D037613 | 110838 | V5.0 | BTFM.RM.2.4.1, BTFM.RM.2.7 |
| QCA61x4A | D028340 | 81685 | V4.2 | BTFM.RM.2.4/2.2.c2/2.6 |
| QCA6174 | D022590 | 54917 | V4.1 | RF & RF PHY |
| WCN3660(A/B), WCN3680(B), WCN3610/15/20, MSM8953/37/17/40/20, MSM8909(W), SDM625/632, SDM439/429(W), APQ8009/17/53 | B018867 | 34203 | V4.0 | RF & RF PHY |
| WCN3660(A/B), WCN3680(B) | D023211 | 67796 | V4.1 | RF & RF PHY |
| WCN3660(A/B), WCN3680(B) | B021332 | 47905 | V4.0 | RF & RF PHY |
| MSM8953, SDM625/632, SDM439/429(W), APQ8009/17/53 | D039229 | 112708 | V5.0 | CNSS.PR.4.0.6 and variants |

---

## 2.2 Host QDID/DN (by Android OS Version)

| Android Version | Declaration ID | QDID/DN | BT Spec Ver | Type | Notes |
|----------------|---------------|---------|-------------|------|-------|
| W (Android 16) | Q347779 | — | V6.1 | Core Host | CS+LEA |
| V (Android 15) | Q307060 | — | V6.0 | Core Host | LE Audio |
| U (Android 14) | D064514 | 222137 | V5.4 | Component | LE Audio; Host Subsystem: D064486 |
| T (Android 13) | D059723 | 194861 | V5.3 | Component | LE Audio, no PBP |
| T (Android 13) | D060635 | 198016 | V5.3 | Component | LE Audio, with PBP |
| S (Android 12) | D057039 | 176512 | V5.2 | Component | LE Audio; Host Subsystem: D057038 |
| S (Android 12) | D057041 | 176546 | V5.2 | Component | NO LE Audio; Host Subsystem: D057040 |
| R (Android 11) | D050631 | 149467 | V5.2 | Component | Host Subsystem: D050632 |
| Q (Android 10) | D034494 | 138963 | V5.1 | Component | Host Subsystem: D043746 |
| P (Android 9) | D039507 | 112718 | V5.0 | Component | Host Subsystem: D039164 |
| P (Android 9) | D037810 | 100515 | V5.0 | Component | Host Subsystem: D023374 |
| O (Android 8) | D031081 | 91403 | V5.0 | Host Subsystem | — |
| O (Android 8) | D031080 | 86918 | V5.0 | Host Subsystem | — |
| N (Android 7) | D024526 | 78979 | V4.2 | Host Subsystem | — |
| M (Android 6) | D026808 | 73778 | V4.2 | Host Subsystem | — |
| L (Android 5) | D023373 | 62309 | V4.1 | Host Subsystem | — |
| KK (Android 4.4) | D021773 | 72291 | V4.2 | Host Subsystem | — |
| KK (Android 4.4) | D021772 | 54566 | V4.0 | Host Subsystem | — |

---

## BT Version Rule

**Final BT version = min(Host BT version, Controller BT version)**

Example: Host is Android S (V5.2) + Controller is WCN3680B (V4.0/V4.1) → **BT 4.0 or 4.1**

---

## Notes on WCN3680/WCN3660 Family

- WCN3660A, WCN3660B, WCN3680B: Covered by B018867 (QDID 34203, V4.0) and B021332 (QDID 47905, V4.0)
- WCN3680B also covered by D023211 (QDID 67796, V4.1)
- These are older chips; BT version is 4.0 or 4.1 regardless of Android version
