REF_PATH = "/home/cc/nextflow/reference-files"
ref_fa = Channel.fromPath(REF_PATH + '/*.fa')
ref_amb = Channel.fromPath(REF_PATH + '/*.amb')
ref_ann = Channel.fromPath(REF_PATH + '/*.ann')
ref_bwt = Channel.fromPath(REF_PATH + '/*.bwt')
ref_fai = Channel.fromPath(REF_PATH + '/*.fai')
ref_pac = Channel.fromPath(REF_PATH + '/*.pac')
ref_sa = Channel.fromPath(REF_PATH + '/*.sa')
ref_dict = Channel.fromPath(REF_PATH + '/*.dict')
genome_dir = Channel.fromPath(REF_PATH + '/star-2.7.5c_GRCh38.d1.vd1_gencode.v36')

/* Config */
num_thread = 16

READ_PATH = "/home/cc/nextflow/read-files/SRR6490021"
meta_id = Channel.of(READ_PATH.tokenize('/')[-1])
fastq_pair = Channel.fromFilePairs(READ_PATH + '/SRR*_{1,2}.fastq', flat: true)
                    .splitFastq(by: 4000000, limit:4000000, pe:true, file: true)

process STAR2 {
    container "ghcr.io/martinluttap/star2:2.7.10b"
    
    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path genome_dir
        val num_thread

    script:
        """
        STAR --readFilesIn ${forward_fastq} ${reverse_fastq} --outSAMattrRGline ID:RG_ID_${meta} SM:RG_SM_${meta} PL:RG_PL${meta} --alignIntronMax 1000000 --alignIntronMin 20 --alignMatesGapMax 1000000 --alignSJDBoverhangMin 1 --alignSJoverhangMin 8 --alignSoftClipAtReferenceEnds Yes --chimJunctionOverhangMin 15 --chimMainSegmentMultNmax 1 --chimOutJunctionFormat 1 --chimOutType Junctions SeparateSAMold WithinBAM SoftClip --chimSegmentMin 15 --genomeDir ${genome_dir} --genomeLoad NoSharedMemory --limitSjdbInsertNsj 1200000 --outFileNamePrefix ${meta}.pe. --outFilterIntronMotifs None --outFilterMatchNminOverLread 0.33 --outFilterMismatchNmax 999 --outFilterMismatchNoverLmax 0.1 --outFilterMultimapNmax 20 --outFilterScoreMinOverLread 0.33 --outFilterType BySJout --outSAMattributes NH HI AS nM NM ch --outSAMstrandField intronMotif --outSAMtype BAM Unsorted --outSAMunmapped Within --quantMode TranscriptomeSAM GeneCounts --readFilesCommand zcat --runThreadN ${num_thread} --twopassMode Basic
        """
}

workflow {
    STAR2(
        fastq_pair, genome_dir, num_thread
    )
}