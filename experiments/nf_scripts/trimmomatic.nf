/* REFERENCE FILES */
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

READ_PATH = "/home/cc/nextflow/read-files/SRR6490021"
meta_id = Channel.of(READ_PATH.tokenize('/')[-1])
fastq_pair = Channel.fromFilePairs(READ_PATH + '/SRR*_{1,2}.fastq', flat: true)
                    .splitFastq(by: 400000, limit:400000, pe:true, file: true)

process TRIMMOMATIC {
    container "ghcr.io/martinluttap/trimmomatic:0.38"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
		
    script:
        """
        java -Xmx4G -jar /bin/trimmomatic.jar PE -threads 40 -baseout ${forward_fastq.getBaseName()}.fq.gz -validatePairs ${forward_fastq} ${reverse_fastq} TOPHRED33
        """        
}

workflow {
    TRIMMOMATIC(
        fastq_pair
    )
}