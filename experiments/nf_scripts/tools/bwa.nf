import groovy.time.TimeCategory 
import groovy.time.TimeDuration

REF_PATH = "/home/cc/nextflow/reference-files"
ref_fa = Channel.fromPath(REF_PATH + '/*.fa')
ref_amb = Channel.fromPath(REF_PATH + '/*.amb')
ref_ann = Channel.fromPath(REF_PATH + '/*.ann')
ref_bwt = Channel.fromPath(REF_PATH + '/*.bwt')
ref_fai = Channel.fromPath(REF_PATH + '/*.fai')
ref_pac = Channel.fromPath(REF_PATH + '/*.pac')
ref_sa = Channel.fromPath(REF_PATH + '/*.sa')
ref_dict = Channel.fromPath(REF_PATH + '/*.dict')

num_threads = params.num_threads
READ_PATH = "/home/cc/nextflow/read-files/SRR24039108"

Date loadStart = new Date()
println ("Data loading started ...")
fastq_pair = Channel.fromFilePairs(READ_PATH + '/*_{1,2}.fastq', flat: true)
                    .splitFastq(by: 500000, limit:500000, pe:true, file: true)

fastq_pair2 = Channel.fromFilePairs(READ_PATH + '/*_{1,2}.fastq', flat: true)
            .splitFastq(by: 250000, limit:250000, pe:true, file: true)

process BWA {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict

    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 8 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}

process BWA_32c {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"
    containerOptions '--cpus=32'

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict

    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 64 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
        
}

process BWA_16c {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"
    containerOptions '--cpus=16'

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict

    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 16 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
        
}

process BWA_8c {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"
    containerOptions '--cpus=8'
    
    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 8 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
        
}

process BWA_4c {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"
    containerOptions '--cpus=4'

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 16 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}

process BWA_NO_LIMIT {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 96 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}

process BWA_NO_LIMIT2 {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 32 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}

process BWA_NO_LIMIT3 {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 32 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}

process BWA_NO_LIMIT4 {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 32 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}

process BWA_NO_LIMIT5 {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 32 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}

process BWA_NO_LIMIT6 {
    container "ghcr.io/martinluttap/bwa:0.7.15-554c2eb"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
    output:
        path "*.bam"

    script: 
        METADATA = "\"@RG\\tID:SRR24039108\\tPL:ILLUMINA\\tSM:Sample\""
        """
        bwa mem -t 32 -T 0 -R ${METADATA} ${ref_fa} ${forward_fastq} ${reverse_fastq} | samtools view -Shb -o SRR24039108.bam -
        """
}
