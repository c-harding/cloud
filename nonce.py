#!/usr/bin/env python3

import sys
from hashlib import sha256
from datetime import datetime
from typing import Callable, Union
from shlex import quote
from math import log, sqrt, ceil, floor

import boto3
from botocore.exceptions import ClientError

AMI = 'ami-0ad788d4ae566815b'
TIER = 't2.micro'
QUEUE_NAME = 'NonceOutput'
REGION = 'us-east-2'
IAM = 'arn:aws:iam::041385281611:instance-profile/nonce-queue-role'


def create_ec2_instance(image_id, instance_type, user_data):
    # Provision and launch the EC2 instance
    ec2_client = boto3.client('ec2', region_name=REGION)
    try:
        response = ec2_client.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            MinCount=1,
            IamInstanceProfile=dict(Arn=IAM),
            MaxCount=1,
            UserData=user_data)
    except ClientError as e:
        print(e, file=sys.stderr)
        return None
    return response['Instances'][0]


def get_queue():
    sqs = boto3.resource('sqs', region_name=REGION)
    return sqs.get_queue_by_name(QueueName='NonceOutput')


def send_success(nonce, zeros, id):
    queue = get_queue()
    return queue.send_message(MessageBody=f'FOUND {nonce} with {zeros}', MessageAttributes={
        'Id': {
            'DataType': 'String',
            'StringValue': id,
        }})


def bash_write_file(source, location) -> str:
    with open(source) as f:
        return '\n'.join([
            f"cat << 'EOF' > {location}",
            f.read(),
            'EOF',
        ])


def generate_user_data(block, difficulty, step=1, start=0, id=""):
    block_string = str(block, 'utf8')
    return "\n".join([
        '#!/bin/bash',
        bash_write_file(__file__, '~/nonce.py'),
        'chmod u+x ~/nonce.py',
        f'~/nonce.py slave {quote(block_string)} {difficulty} {step} {start} {id} 2> ~/nonce.log',
    ])


def create_nonce_VM(block, difficulty, step=1, start=0, id=""):
    instance = create_ec2_instance(
        AMI, TIER,
        user_data=generate_user_data(block, difficulty, step, start, id))
    return instance


def master_nonce_search(block, difficulty, n):
    start_time = datetime.now()
    id = str(start_time.timestamp())
    ec2 = boto3.resource('ec2', region_name=REGION)
    instances = []
    try:
        for i in range(n):
            instances.append(
                ec2.Instance(id=create_nonce_VM(block, difficulty, n, i, id)["InstanceId"]))
        print(f'Created after {datetime.now() - start_time}')
        if n is 1:
            for instance in instances:
                instance.wait_until_running()
                instance.load()
                print(instance.public_dns_name)
            print(f'All running after {datetime.now() - start_time}')
        queue = get_queue()
        while True:
            for message in queue.receive_messages(WaitTimeSeconds=20, MessageAttributeNames=['All']):
                if (message.message_attributes is not None
                        and 'Id' in message.message_attributes
                        and message.message_attributes['Id']['StringValue'] == id):
                    print(f'Found after {datetime.now() - start_time}')
                    print(message.body)
                    message.delete()
                    return
                else:
                    message.delete()
    finally:
        for instance in instances:
            instance.terminate()


def get_stdin() -> bytes:
    return bytes(sys.stdin.readline(), 'utf8')


def sha(block: bytes) -> bytes:
    SHA256 = sha256()
    SHA256.update(block)
    return SHA256.digest()


def leading_zeros(hash: bytes) -> int:
    i = 0
    for c in hash.hex():
        if c == '0':
            i += 4
            continue
        elif int(c, 16) < 2:
            i += 3
        elif int(c, 16) < 4:
            i += 2
        elif int(c, 16) < 8:
            i += 1
        break
    return i


def build_nonce(block: bytes, number: int) -> bytes:
    return (block + number.to_bytes(4, byteorder='big'))


def sha2(block: bytes) -> bytes:
    return sha(sha(block))


def find_nonce(block: bytes, difficulty: int, step=1, start=0) -> (int, int):
    for nonce in range(start, 2**32, step):
        bytestring = build_nonce(block, nonce)
        hash = sha2(bytestring)
        zeros = leading_zeros(hash)
        if zeros >= difficulty:
            return nonce, zeros
    else:
        return (-1, 0)


def print_nonce_result(nonce: int, zeros: int) -> None:
    print(f'Found nonce {nonce} with {zeros} leading zeros')


def get_arg(i: str, fallback: Union[str, Callable[[], str]]):
    try:
        return sys.argv[i]
    except IndexError:
        return fallback() if callable(fallback) else fallback


def get_int_arg(i: int, fallback: Union[int, Callable[[], int]]):
    try:
        return int(sys.argv[i], 10)
    except IndexError:
        return fallback() if callable(fallback) else fallback


def main():
    mode = get_arg(1, '')
    block = bytes(get_arg(2, 'COMSM0010cloud'), 'utf8')
    difficulty = get_int_arg(3, 20)

    if mode == 'slave':
        step = get_int_arg(4, 1)
        start = get_int_arg(5, 0)
        id = get_arg(6, 0)
        send_success(*find_nonce(block, difficulty, step, start), id)
    elif mode == 'local':
        print_nonce_result(*find_nonce(block, difficulty, 1, 0))
    elif mode == 'master':
        n = get_int_arg(4, 1)
        master_nonce_search(block, difficulty, n)
    elif mode == 'auto':
        t = get_int_arg(5, 600)
        p = get_int_arg(5, 90)
        print(f'{t} seconds requested to find a golden nonce with',
              f'{difficulty} bits with {p}% confidence')
        # found using the quadratic formula, and explained in the report
        if p is 100:
            x = 2**32
        else:
            x = min(2**32, log(1-p/100, 1-0.5**difficulty))
        discriminant = ((t-30)**2 - 8/165000 * x)
        lower_bound = (t-30 - sqrt(discriminant))/4
        upper_bound = (t-30 + sqrt(discriminant))/4
        print(f'{lower_bound} < n < {upper_bound}')
        if ceil(lower_bound) > floor(upper_bound):
            print('No such values for n exist, aborting')
        else:
            print(f'Chosen n = {ceil(lower_bound)}')
            master_nonce_search(block, difficulty, ceil(lower_bound))
    else:
        print("Error: no mode given. Modes: slave, local, master, auto",
              file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
