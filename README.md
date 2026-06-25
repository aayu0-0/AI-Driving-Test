# 🚗 AI-Driving-Test

An AI-powered driver behavior analysis system built using OpenCV that evaluates driving performance from road footage and generates a comprehensive driving assessment report.

> **Note:** This project is intended for educational and research purposes. It demonstrates how computer vision can be used to analyze driving behavior and road conditions.

---

## 📌 Overview

Road safety depends heavily on driver awareness and driving habits. This project leverages computer vision techniques to analyze driving videos and evaluate driving performance based on lane discipline and road observations.

Instead of simply detecting lanes, the system provides an assessment of driving quality by processing video frames, identifying driving events, and generating a final driving report.

---

## ✨ Features

* 🚗 Lane Detection
* 📹 Video Frame Processing
* 📊 Driving Performance Analysis
* 📈 Driving Score Generation
* 📝 Automatic Driving Report
* ⚡ Real-time Visualization

---

## 🛠️ Technologies Used

* Python 3.x
* OpenCV
* NumPy

---

## 📂 Project Structure

```text
AI-Driving-Test/
│
├── assets/               # Images and GIFs
├── data/                 # Input driving video
├── src/                  # Source code
├── output/               # Processed output videos
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 📥 Dataset

The driving video used in this project is **not included** in this repository to keep the repository lightweight.

Download the dataset from Kaggle:

**https://www.kaggle.com/datasets/dpamgautam/video-file-for-lane-detection-project/data**

After downloading:

1. Extract the ZIP file.
2. Create a `data/` folder if it doesn't already exist.
3. Place the video inside the folder.

Your directory should look like:

```text
AI-Driving-Test/
│
├── data/
│   └── test_video.mp4
├── src/
└── README.md
```

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/AI-Driving-Test.git
cd AI-Driving-Test
```

Install the required packages:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Project

Once the dataset has been downloaded and placed inside the `data/` folder, run:

```bash
python src/main.py
```

The processed video and analysis results will be displayed and can be saved in the `output/` directory.

---

## 📊 Workflow

```text
Input Video
      │
      ▼
Frame Extraction
      │
      ▼
Pre-processing
      │
      ▼
Lane Detection
      │
      ▼
Road Analysis
      │
      ▼
Driving Performance Evaluation
      │
      ▼
Final Driving Report
```

---

## 📸 Results

The project produces:

* Lane visualization
* Processed video output
* Driving performance analysis
* Driving score
* Summary report

*(Add screenshots or GIFs here.)*

---

## 🚀 Future Improvements

* Traffic Sign Detection
* Vehicle Detection
* Speed Estimation
* Driver Drowsiness Detection
* Steering Angle Estimation
* Real-time Dashboard
* AI-based Driving Recommendations

---

## 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

If you'd like to contribute:

1. Fork the repository.
2. Create a new branch.
3. Commit your changes.
4. Submit a Pull Request.

---

## 📜 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Aayush Sardana**

B.Tech – Instrumentation and Control Engineering
Dr. B.R. Ambedkar National Institute of Technology, Jalandhar

If you found this project useful, consider giving it a ⭐ on GitHub!
