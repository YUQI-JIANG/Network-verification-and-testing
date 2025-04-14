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

def random_ip() -> str:
    a = random.randint(1, 223)
    b = random.randint(0, 255)
    c = random.randint(0, 255)
    d = random.randint(0, 255)
    return f"{a}.{b}.{c}.{d}"

def random_mask() -> int:
    return random.randint(MIN_MASK, MAX_MASK)

def generate_valid_ip_and_mask():
    while True:
        ip = random_ip()
        mask = random_mask()
        net = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj != net.network_address and ip_obj != net.broadcast_address:
            return ip, mask

def compute_last_host_addr(ip: str, mask: int) -> str:
    bc_addr = ipaddress.ip_interface(f"{ip}/{mask}").network.broadcast_address
    last_host_int = int(bc_addr) - 1
    last_host_obj = ipaddress.ip_address(last_host_int)
    return f"{last_host_obj}/{mask}"

def flip_last_host_bits(last_host_int: int, mask: int, flips: int = 1) -> int:
    host_bits = 32 - mask
    bc_int = last_host_int + 1
    net_mask = ~((1 << host_bits) - 1) & 0xFFFFFFFF
    net_int = bc_int & net_mask

    net_positions = list(range(host_bits, 32))
    chosen = random.sample(net_positions, flips)

    fake_net_int = net_int
    for pos in chosen:
        fake_net_int ^= (1 << pos)

    host_mask = (1 << host_bits) - 1
    fake_bc_int = fake_net_int | host_mask

    fake_last_int = fake_bc_int - 1
    return fake_last_int

def generate_distractors(correct_last: str, delta: int = MASK_PERTURB_DELTA) -> list[str]:
    ip_str, mask_str = correct_last.split('/')
    original_mask = int(mask_str)
    last_host_obj = ipaddress.ip_interface(correct_last).ip
    last_host_int = int(last_host_obj)

    lo = max(MIN_MASK, original_mask - delta)
    hi = min(MAX_MASK, original_mask + delta)

    candidate_addresses = set()

    for m in range(lo, hi + 1):
        if m == original_mask:
            continue
        tmp_bc = ipaddress.ip_network(f"{ip_str}/{m}", strict=False).broadcast_address
        tmp_last_int = int(tmp_bc) - 1
        tmp_last_obj = ipaddress.ip_address(tmp_last_int)

        if tmp_last_obj != last_host_obj:
            candidate_addresses.add(f"{tmp_last_obj}/{original_mask}")

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
        fake_int = flip_last_host_bits(last_host_int, original_mask, flips)

        if fake_int == last_host_int:
            continue
        fake_obj = ipaddress.ip_address(fake_int)
        fake_str = f"{fake_obj}/{original_mask}"

        if fake_int != last_host_int and fake_str not in distractors_set:
            distractors_set.add(fake_str)

    return list(distractors_set)[:NUM_DISTRACTORS]

def main():
    num_questions = NUM_QUESTIONS
    filename = "Find_Last_Host_Address.txt"

    with open(filename, "w", encoding="utf-8") as f:
        for i in range(1, num_questions + 1):
            ip, mask = generate_valid_ip_and_mask()
            correct_last = compute_last_host_addr(ip, mask)
            distractors = generate_distractors(correct_last, MASK_PERTURB_DELTA)

            choices = [correct_last] + distractors
            random.shuffle(choices)

            gift_choices_str = ""
            for c in choices:
                if c == correct_last:
                    gift_choices_str += f"={c}\n"
                else:
                    gift_choices_str += f"~{c}\n"

            question_title = f"Find Last Host Address Q{i}"

            if SHOW_BINARY:
                bin_ip = ip_to_binary_str(ip)
                question_text = (
                    f"An IP address {ip} ({bin_ip}) has a subnet mask of /{mask}. "
                    "Which of the following is the LAST host address for this IP?"
                )
            else:
                question_text = (
                    f"An IP address {ip} has a subnet mask of /{mask}. "
                    "Which of the following is the LAST host address for this IP?"
                )

            gift_block = (
                f"::{question_title}::\n"
                f"{question_text}\n"
                "{\n"
                f"{gift_choices_str}"
                "}\n\n"
            )
            f.write(gift_block)

    print(f"{num_questions} multiple choice questions about LAST host addresses have been generated in {filename}")

if __name__ == "__main__":
    main()
