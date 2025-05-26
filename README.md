#  Network Address Quiz Generator

This repository contains Python scripts that auto-generate IP networking multiple-choice quizzes. Each script creates 100 questions focused on one type of address calculation (e.g., network address, broadcast address, last Host Address and first Host Address).


##  Project Structure

Output/
├── Find_Broadcast_Address.txt
├── Find_First_Host_Address.txt
├── Find_Last_Host_Address.txt
└── Find_Network_Address.txt

Scripts/
├── Find Broadcast Address.py
├── Find First Host Address.py
├── Find Last Host Address.py
└── Find Network Address.py

###  File Descriptions

| File Name                        | Description                               |
|----------------------------------|-------------------------------------------|
| `Find_Broadcast_Address.txt`     | Output file: Broadcast address questions  |
| `Find_First_Host_Address.txt`    | Output file: First host address questions |
| `Find_Last_Host_Address.txt`     | Output file: Last host address questions  |
| `Find_Network_Address.txt`       | Output file: Network address questions    |
| `Find Broadcast Address.py`      | Script to generate broadcast address      |
| `Find First Host Address.py`     | Script to generate first host address     |
| `Find Last Host Address.py`      | Script to generate last host address      |
| `Find Network Address.py`        | Script to generate network address        |


##  Script Purpose

Each script:

- Randomly generates 100 IP address and subnet mask combinations.
- Calculates the correct answer for the topic (e.g., broadcast address).
- Creates 3 incorrect distractor options.
- Writes all questions in a readable format into a `.txt` file, including the correct answer marked with `=`.


##  Question Format Example (Broadcast Address)

Each question has the following format:

::Find Broadcast Address Q1::
An IP address 62.247.110.181 (00111110.11110111.01101110.10110101) has a subnet mask of /11. 
Which of the following is the broadcast address for this IP?

{
~62.191.255.255/11
~54.255.255.255/11
~63.223.255.255/11
=62.255.255.255/11
}

- The binary form of the IP address is shown in parentheses.
- The options are enclosed in `{}` and:
  - One is correct (marked with `=`).
  - Three are incorrect but plausible.


##  How to Run

Run any of the Python scripts from the `Scripts` folder using:

```bash
python "Find Broadcast Address.py"
```

After execution, the corresponding `.txt` file will be generated in the `Output/` folder.


##  Scripts Overview

| Script Name                   | Address Type        | Output File                          |
|------------------------------|---------------------|--------------------------------------|
| Find Broadcast Address.py     | Broadcast Address    | Output/Find_Broadcast_Address.txt     |
| Find Network Address.py       | Network Address      | Output/Find_Network_Address.txt       |
| Find First Host Address.py    | First Usable Host    | Output/Find_First_Host_Address.txt    |
| Find Last Host Address.py     | Last Usable Host     | Output/Find_Last_Host_Address.txt     |

Each script is independent and can be run separately.


##  Use Cases

- Study material for networking and subnetting.
- Practice quizzes for students.
- Automatically generated datasets for grading.


##  Requirements

- Python 3.6+.
- No external libraries required (`ipaddress` is from standard library).


##  Author

Aim of the thesis is to focus on the basic background on computer networking (e.g., IP addressing and routing) and develop an automatic generator of problems for the students, to be integrated in Politecnico Moodle 
platform (https://moodle.org/). A possible option could be to integrate Moodle with Kathara labs (https://www.kathara.org/).
