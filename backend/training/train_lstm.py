import torch
import torch.nn as nn
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from torch.utils.data import TensorDataset, DataLoader

# ================= DATA =================
data = pd.read_csv("fire_timeseries.csv")

X = data[["wind", "dir", "severity", "humidity"]].values
y = data["spread"].values

X = torch.tensor(X).float().unsqueeze(1)
y = torch.tensor(y).long()

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

train_dataset = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)

# ================= MODEL =================
class FireLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(4, 32, batch_first=True)
        self.fc = nn.Linear(32, 3)
        self.register_buffer("mean", torch.tensor([11.022466, 177.8312, 1.9988, 55.2473]))
        self.register_buffer("std", torch.tensor([5.20969696, 103.75680437, 0.81514723, 20.59177372]))

    def forward(self, x):
        # Normalize input
        x = (x - self.mean) / self.std
        out, _ = self.lstm(x)
        return self.fc(out[:, -1])

model = FireLSTM()
loss_fn = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.005)

# ================= TRAIN =================
for epoch in range(100):
    model.train()
    total_loss = 0
    for batch_x, batch_y in train_loader:
        optimizer.zero_grad()
        pred = model(batch_x)
        loss = loss_fn(pred, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * batch_x.size(0)
    
    epoch_loss = total_loss / len(X_train)
    if (epoch + 1) % 10 == 0 or epoch == 0:
        print(f"Epoch {epoch+1}/100 | Loss: {epoch_loss:.4f}")

# ================= TEST =================
model.eval()
with torch.no_grad():
    y_pred = model(X_test).argmax(dim=1)
    acc = accuracy_score(y_test, y_pred)
    print("LSTM Accuracy:", f"{acc*100:.2f}%")

# ================= SAVE =================
torch.save(model.state_dict(), "fire_lstm.pth")
print("fire_lstm.pth saved")
