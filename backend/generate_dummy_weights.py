import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Define the exact same architecture as app.py
class DeforestationCNN(nn.Module):
    def __init__(self):
        super(DeforestationCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(32 * 32 * 32, 128)
        self.fc2 = nn.Linear(128, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = self.relu(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return x

print("Initializing model...")
model = DeforestationCNN()

# Generate Synthetic Training Data
# 100 samples of 3-channel 128x128 images
print("Generating synthetic dataset (100 samples)...")
X_train = torch.rand(100, 3, 128, 128)
y_train = torch.randint(0, 2, (100, 1)).float()  # Binary labels: 0 or 1

dataset = TensorDataset(X_train, y_train)
loader = DataLoader(dataset, batch_size=10, shuffle=True)

# Training setup
criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Quick "training" loop
epochs = 5
print(f"Starting simulated training for {epochs} epochs...")
for epoch in range(epochs):
    running_loss = 0.0
    for inputs, labels in loader:
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    print(f"Epoch {epoch+1}/{epochs} - Loss: {running_loss/len(loader):.4f}")

# Save the weights
os.makedirs("training", exist_ok=True)
save_path = "training/deforestation_cnn.pth"
torch.save(model.state_dict(), save_path)
print(f"\n✅ Synthetically trained weights saved successfully to {save_path}")
