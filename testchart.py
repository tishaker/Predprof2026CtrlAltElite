import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Тестовые данные
scores = [250, 270, 280, 290, 300, 310, 320, 330, 340, 350, 360, 370, 380]

plt.figure(figsize=(8, 4))
plt.hist(scores, bins=5, edgecolor='black', alpha=0.7)
plt.xlabel('Баллы')
plt.ylabel('Количество')
plt.title('Тестовая гистограмма')
plt.savefig('test_chart.png')
print("✅ Тестовый график создан: test_chart.png")
plt.close()