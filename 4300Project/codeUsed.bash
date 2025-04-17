mkdir 4300Proj
cd 4300Proj
fastq-dump --split-files --gzip SRR30853069
fastq-dump --split-files SRR30853069
(base) root@LAPTOP-MHBH272L:~/4300Proj# mkdir -p fastqc assembly quast annotation blast


actually

wget ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR308/069/SRR30853069/SRR30853069_1.fastq.gz
wget ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR308/069/SRR30853069/SRR30853069_2.fastq.gz

#Initialize Project

mkdir 4300Project
#mkdir -p ~/4300Proj/{fastqc_results,assembly,annotation,blast}
cd 4300Project

#Source & Reference
#https://www.ncbi.nlm.nih.gov/datasets/genome/?taxon=44744
#https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/GCA_030144725.1/download?include_annotation_type=GENOME_FASTA&include_annotation_type=GENOME_GFF&include_annotation_type=RNA_FASTA&include_annotation_type=CDS_FASTA&include_annotation_type=PROT_FASTA&include_annotation_type=SEQUENCE_REPORT&hydrated=FULLY_HYDRATED


#Working seqs
#https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_011766145.1/
wget ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR322/026/SRR32280526/SRR32280526_1.fastq.gz
wget ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR322/026/SRR32280526/SRR32280526_2.fastq.gz

#fastqc SRR32280526_1.fastq.gz SRR32280526_2.fastq.gz
fastqc  SRR32280526_1.fastq.gz SRR32280526_2.fastq.gz


#Trimming
(base) root@LAPTOP-MHBH272L:~/4300Proj# conda activate trimmomatic_env

trimmomatic PE -phred33 \
  SRR32280526_1.fastq.gz SRR32280526_2.fastq.gz \
  trimmed_reads/SRR32280526_1_paired.fastq.gz trimmed_reads/SRR32280526_1_unpaired.fastq.gz \
  trimmed_reads/SRR32280526_2_paired.fastq.gz trimmed_reads/SRR32280526_2_unpaired.fastq.gz \
  ILLUMINACLIP:adapters/TruSeq3-PE.fa:2:30:10 \
  LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36



(trimmomatic_env) root@LAPTOP-MHBH272L:~/4300Proj# trimmomatic PE -phred33 \
  SRR32280526_1.fastq.gz SRR32280526_2.fastq.gz \
  SRR32280526_1_trimmed_paired.fastq.gz SRR32280526_1_trimmed_unpaired.fastq.gz \
  SRR32280526_2_trimmed_paired.fastq.gz SRR32280526_2_trimmed_unpaired.fastq.gz \
  LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36

conda deactivate

#Run SPADES
conda activate spades_env



conda deactivate



megahit -1 SRR32280526_1_trimmed_paired.fastq.gz -2 SRR32280526_2_trimmed_paired.fastq.gz


conda activate conda_env 

quast.py assembly/spades_output/scaffolds.fasta megahit_out/final.contigs.fa \
  -r reference/nostoc_sp_c117_reference.fasta \
  -o fastqc_results/quast_output

conda deactivate

conda activate prokka_env

prokka --outdir annotation/prokka_output --prefix nostoc_sp_c117 \
  --genus Nostoc --species "sp. C117" --strain C117 --kingdom Bacteria \
  --cpus 4 --centre X --compliant --force \
  assembly/spades_output/scaffolds.fasta

deactivate


mkdir -p blast/results


blastp -query annotation/prokka_output/nostoc_sp_c117.faa \
  -db blast/db/swissprot \
  -outfmt "6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle" \
  -evalue 1e-10 -max_target_seqs 1 \
  -out blast/results/nostoc_sp_c117_swissprot.blastp