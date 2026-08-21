# ZBRANO wake-word model

`hey_zbrano.onnx` is the first ZBRANO OpenWakeWord baseline model. It is
included for silent shadow-mode evaluation and must not activate chat until
real-room testing establishes an acceptable threshold.

- Phrase: `Hey ZBRANO`
- Training pronunciation: `hˈeɪ zbɹˈɑːnoʊ`
- SHA-256: `7ab701e62e79b0d4a4d996417102b96907a25a9fd5ebe34f9ca1eb509ec4df42`
- Training evaluation: accuracy 83.37%, recall 66.96%, false positives 3.54/hour
- Model format: ONNX, 205,430 bytes

The model was trained using ACAV100M-derived negative features and is provided
for this personal, non-commercial project under CC BY-NC-SA 4.0. OpenWakeWord
runtime code is Apache-2.0 licensed.
