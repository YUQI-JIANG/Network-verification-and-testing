import random
import ipaddress

MIN_MASK = 8        
MAX_MASK = 30       
NUM_QUESTIONS = 100 
NUM_DISTRACTORS = 3 
MASK_PERTURB_DELTA = 6 
SHOW_BINARY = True

def ip_to_binary_str(ip_str: str) -> str:
    parts = ip_str.split('.')
    bparts = []
    for p in parts:
        p_int = int(p)
        b = f"{p_int:08b}"  
        bparts.append(b)
    return ".".join(bparts)

def random_ip():
    a = random.randint(1, 223)
    b = random.randint(0, 255)
    c = random.randint(0, 255)
    d = random.randint(0, 255)
    return f"{a}.{b}.{c}.{d}"

def random_mask():
    return random.randint(MIN_MASK, MAX_MASK)

def generate_valid_ip_and_mask():
    while True:
        ip = random_ip()
        mask = random_mask()
        net = ipaddress.ip_network(f"{ip}/{mask}", strict=False) 
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj != net.network_address and ip_obj != net.broadcast_address:
            return ip, mask

def compute_first_host_addr(ip, mask):
    net_addr = ipaddress.ip_interface(f"{ip}/{mask}").network.network_address
    first_host_int = int(net_addr) + 1
    first_host_addr = ipaddress.ip_address(first_host_int)
    return f"{first_host_addr}/{mask}"

def flip_network_bits_for_first_host(first_host_int: int, mask: int, flips: int = 1) -> int:
    host_bits = 32 - mask
    net_positions = list(range(host_bits, 32))
    net_int = first_host_int & ~((1 << host_bits) - 1)
    chosen = random.sample(net_positions, flips)

    fake_int = net_int
    for pos in chosen:
        fake_int ^= (1 << pos) 

    fake_int += 1  
    return fake_int

def generate_distractors(correct_first: str, delta: int = MASK_PERTURB_DELTA) -> list[str]:
    ip_str, mask_str = correct_first.split('/')
    original_mask = int(mask_str)
    correct_first_obj = ipaddress.ip_interface(correct_first).ip
    correct_first_int = int(correct_first_obj) 

    lo = max(MIN_MASK, original_mask - delta)
    hi = min(MAX_MASK, original_mask + delta)
   
    candidate_addresses = set()

    for mask in range(lo, hi + 1):
        if mask == original_mask:
            continue
        tmp_network = ipaddress.ip_network(f"{ip_str}/{mask}", strict=False)
        tmp_net_addr = tmp_network.network_address
        tmp_first_host_int = int(tmp_net_addr) + 1
        tmp_first_host_ip = ipaddress.ip_address(tmp_first_host_int)

        if tmp_first_host_ip != correct_first_obj:
            candidate_addresses.add(f"{tmp_first_host_ip}/{original_mask}")

    candidate_addresses = list(candidate_addresses)
    random.shuffle(candidate_addresses)

    distractors_set = set(candidate_addresses[:NUM_DISTRACTORS])

    if len(distractors_set) >= NUM_DISTRACTORS:
        return list(distractors_set)[:NUM_DISTRACTORS]
    
    tries = 0
    max_tries = 1000

    while len(distractors_set) < NUM_DISTRACTORS and tries < max_tries:
        tries += 1
        flips = random.choice([1, 2])
        fake_int = flip_network_bits_for_first_host(correct_first_int, original_mask, flips)

        if fake_int == correct_first_int:
            continue  

        fake_ip_obj = ipaddress.ip_address(fake_int)
        fake_str = f"{fake_ip_obj}/{original_mask}"

        if fake_int != correct_first_int and fake_str not in distractors_set:
            distractors_set.add(fake_str)

    return list(distractors_set)[:NUM_DISTRACTORS]

def main():

    num_questions = NUM_QUESTIONS
    filename = "Find_First_Host_Address.txt"

    with open(filename, "w", encoding="utf-8") as f:
        for i in range(1, num_questions+1):
            ip, mask = generate_valid_ip_and_mask()
            correct_first = compute_first_host_addr(ip, mask)
            distractors = generate_distractors(correct_first, MASK_PERTURB_DELTA)
            
            choices = [correct_first] + distractors
            random.shuffle(choices)

            gift_choices_str = ""
            for c in choices:
                if c == correct_first:
                    gift_choices_str += f"={c}\n"
                else:
                    gift_choices_str += f"~{c}\n"

            question_title = f"Find First Host Address Q{i}"

            if SHOW_BINARY:
                bin_ip = ip_to_binary_str(ip)
                question_text = (
                    f"An IP address {ip} ({bin_ip}) has a subnet mask of /{mask}. "
                    "Which of the following is the FIRST host address for this IP?"
                )
            else:
                question_text = (
                    f"An IP address {ip} has a subnet mask of /{mask}. "
                    "Which of the following is the FIRST host address for this IP?"
                )

            gift_block = (
                f"::{question_title}::\n"
                f"{question_text}\n"
                "{\n"
                f"{gift_choices_str}"
                "}\n\n"
            )

            f.write(gift_block)

    print(f"{num_questions} multiple choice questions about FIRST host addresses have been generated in {filename}")

if __name__ == "__main__":
    main()