REF_PATH = "/home/cc/nextflow/reference-files"
ref_known_sites = Channel.fromPath(REF_PATH + '/*.vcf.gz')
ref_known_sites_tbi = Channel.fromPath(REF_PATH + '/*.vcf.gz.tbi')
ref_fa = Channel.fromPath(REF_PATH + '/*.fa')
ref_amb = Channel.fromPath(REF_PATH + '/*.amb')
ref_ann = Channel.fromPath(REF_PATH + '/*.ann')
ref_bwt = Channel.fromPath(REF_PATH + '/*.bwt')
ref_fai = Channel.fromPath(REF_PATH + '/*.fai')
ref_pac = Channel.fromPath(REF_PATH + '/*.pac')
ref_sa = Channel.fromPath(REF_PATH + '/*.sa')
ref_dict = Channel.fromPath(REF_PATH + '/*.dict')

READ_PATH = "/home/cc/nextflow/read-files/SRR24039108/"
bam = Channel.fromPath(READ_PATH + '/SRR24039108.bam')
num_thread = 1

process PICARD_MARKDUPLICATES {
    container "ghcr.io/martinluttap/picard:2.26.10"

    input:
        path bam

    script:
        """
        java -jar /usr/local/bin/picard.jar MarkDuplicates INPUT=${bam} METRICS_FILE=${bam}.metrics ASSUME_SORT_ORDER=queryname OUTPUT=${bam} TMP_DIR=. VALIDATION_STRINGENCY=STRICT
        """
}

process PICARD_MARKDUPLICATES_SPARK {
    container "ghcr.io/martinluttap/gatk:4.2.4.1"
    containerOptions '--cpus=1'
    cpus 1

    input:
        path bam
        val num_thread

    script:
        """
        java -jar /usr/local/bin/gatk.jar MarkDuplicatesSpark --input ${bam} --metrics-file ${bam}.metrics --output ${bam} --tmp-dir . --read-validation-stringency STRICT --spark-master local[$num_thread]
        """
}

workflow {
    // PICARD_MARKDUPLICATES(
    //     bam
    // )
    PICARD_MARKDUPLICATES_SPARK(
        bam,
        num_thread
    )
}