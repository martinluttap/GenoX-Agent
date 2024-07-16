REF_PATH = "/home/cc/nextflow/reference-files"
ref_fa = Channel.fromPath(REF_PATH + '/*.fa')
ref_amb = Channel.fromPath(REF_PATH + '/*.amb')
ref_ann = Channel.fromPath(REF_PATH + '/*.ann')
ref_bwt = Channel.fromPath(REF_PATH + '/*.bwt')
ref_fai = Channel.fromPath(REF_PATH + '/*.fai')
ref_pac = Channel.fromPath(REF_PATH + '/*.pac')
ref_sa = Channel.fromPath(REF_PATH + '/*.sa')
ref_dict = Channel.fromPath(REF_PATH + '/*.dict')

READ_PATH = "/home/cc/nextflow/read-files/SRR24039108"
NUM_BP = params['NUM_BP'] ?: 100000
fastq_pair = Channel.fromFilePairs(READ_PATH + '/SRR*_{1,2}.fastq', flat: true)
                    .splitFastq(by: NUM_BP, limit:NUM_BP, pe:true, file: true)

process DUMMY {
    input:
        tuple val (meta), path (forward), path (reverse)
    
    script:
        """
        echo
        """
}

workflow {
    DUMMY(
        fastq_pair
    )
}