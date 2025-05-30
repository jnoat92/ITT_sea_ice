#!/bin/bash
#SBATCH --nodes 1
#SBATCH --tasks-per-node=1
#SBATCH --cpus-per-task=40 # change this parameter to 2,4,6,... and increase "--num_workers" accordingly to see the effect on performance
#SBATCH --mem=128G
#SBATCH --time=2:00:00
#SBATCH --output=../output_logs/%j.out
#SBATCH --account=def-dclausi
#SBATCH --mail-user=jnoat92@gmail.com
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=END
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=REQUEUE

# salloc --time=3:00:0 --account=def-dclausi --nodes 1 --tasks-per-node=1 --gpus-per-node=1 --cpus-per-task=8 --mem=32G

echo "No. of task per node: $SLURM_NTASKS"

module purge
module load StdEnv/2020 python/3.9.6
#module load scipy-stack
echo "Loading module done"
source ~/torch_magic1/bin/activate
echo "Activating virtual environment done"

cd ../../Codes
srun python Main_Script_Executor.py
