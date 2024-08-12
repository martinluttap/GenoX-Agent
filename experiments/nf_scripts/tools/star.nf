process STAR_NO_LIMIT_PROD {
    container "ghcr.io/martinluttap/star2:2.7.10b"
    
    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path genome_dir

    script:
        """
        STAR --readFilesIn ${forward_fastq} ${reverse_fastq} --outSAMattrRGline ID:RG_ID_${meta} SM:RG_SM_${meta} PL:RG_PL${meta} --alignIntronMax 1000000 --alignIntronMin 20 --alignMatesGapMax 1000000 --alignSJDBoverhangMin 1 --alignSJoverhangMin 8 --alignSoftClipAtReferenceEnds Yes --chimJunctionOverhangMin 15 --chimMainSegmentMultNmax 1 --chimOutJunctionFormat 1 --chimOutType Junctions SeparateSAMold WithinBAM SoftClip --chimSegmentMin 15 --genomeDir ${genome_dir} --genomeLoad NoSharedMemory --limitSjdbInsertNsj 1200000 --outFileNamePrefix ${meta}.pe. --outFilterIntronMotifs None --outFilterMatchNminOverLread 0.33 --outFilterMismatchNmax 999 --outFilterMismatchNoverLmax 0.1 --outFilterMultimapNmax 20 --outFilterScoreMinOverLread 0.33 --outFilterType BySJout --outSAMattributes NH HI AS nM NM ch --outSAMstrandField intronMotif --outSAMtype BAM Unsorted --outSAMunmapped Within --quantMode TranscriptomeSAM GeneCounts --readFilesCommand zcat --twopassMode Basic --runThreadN 16
        """
}

process STAR_NO_LIMIT_SIMPLE {
    container "ghcr.io/martinluttap/star2:2.7.10b"
    
    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
        path genome_dir

    script:
        """
        STAR --genomeDir ${genome_dir} --outFileNamePrefix ${meta}.pe. --runThreadN 96 --readFilesIn ${forward_fastq} ${reverse_fastq}
        """
}