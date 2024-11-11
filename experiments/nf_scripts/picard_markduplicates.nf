include { PICARD_MARKDUPLICATES as PICARD_MARKDUPLICATES } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/picard_markduplicate.nf"

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

workflow {
    // PICARD_MARKDUPLICATES(
    //     bam
    // )
    PICARD_MARKDUPLICATES_SPARK(
        bam,
        num_thread
    )
}