# Cloud Nonce Discovery

Repository: [github.com/xsanda/cloud](https://github.com/xsanda/cloud)

This program will scan for a golden nonce of a given difficulty.

## Usage

```bash
./nonce.py local <block> <difficulty>
./nonce.py master <block> <difficulty> <n-VMs> [<timeout>]
./nonce.py auto <block> <difficulty> <time-seconds> <percentage-confidence> [<timeout>]
```

If the mode `local` is chosen, the computation will be done without any cloud interaction.
Otherwise, EC2 instances will be used from AWS.
If the mode `master` is used, exactly `<n-VMs>` instances will be used.
If the mode `auto` is used, the minimum number of VMs will be created such that there is a `<percentage-confidence>`% chance of finding a golden nonce in `<time-seconds>` seconds. If this is not possible, no computation will be done.

If a timeout is provided, all the VMs will be shut down after this time, even if no result is found.

To connect to AWS, read the appendix of [the report](report/cloud.pdf) for setup instructions.

The other Python scripts in this folder, `timing_parser*.py`, are used for processing the results of the script, for example when it is run as follows:

```bash
for difficulty in 1 2 5 10; do for n in 1 2 5 10 15 20 25 30 31 32 33; do
echo nonce.py master COMSM0010cloud $difficulty $n >> log.log
./nonce.py master COMSM0010cloud $difficulty $n >> log.log
done; done
```
