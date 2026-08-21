# ZBRANO wake-word model

`hey_zbrano.onnx` is the second ZBRANO OpenWakeWord model. It combines the
original synthetic training corpus with validated real-room recordings. It is
included for silent shadow-mode evaluation and cannot activate chat.

- Phrase: `Hey ZBRANO`
- Training pronunciation: `hˈeɪ zbɹˈɑːnoʊ`
- SHA-256: `0fb509d0c50e4350c3c8fb8c222d0c5d21f49c6479c242f35e0b7f6da97bdf8a`
- Training evaluation: accuracy 84.20%, recall 68.68%, false positives 8.58/hour
- Accepted real-room calibration: 20/21 wake phrases detected and 19/19
  correctly labelled ordinary phrases rejected at threshold 0.50
- Model format: ONNX, 205,430 bytes

The model was trained using ACAV100M-derived negative features and is provided
for this personal, non-commercial project under CC BY-NC-SA 4.0. OpenWakeWord
runtime code is Apache-2.0 licensed.

Runtime feature models from the official OpenWakeWord v0.5.1 release:

- `melspectrogram.onnx`: SHA-256 `ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f`
- `embedding_model.onnx`: SHA-256 `70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f`
