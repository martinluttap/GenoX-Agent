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

READ_PATH = "/home/cc/nextflow/read-files/SRR24039108"
bam = Channel.fromPath(READ_PATH + '/SRR*_sorted.bam')
index = Channel.fromPath(READ_PATH + '/SRR*_sorted.bam.bai')

process GATK4_BASERECALIBRATOR_SPARK {
    container "ghcr.io/martinluttap/gatk:4.2.4.1"

    input:
        path input
        path index
        path known_sites
        path known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
		
    output:
        path "${input.baseName}_bqsr.grp"	, emit: output_grp
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar BaseRecalibratorSpark --output ${input.baseName}_bqsr.grp --input ${input} --known-sites ${known_sites} --reference ${ref_fa}
        """
}

process GATK4_BASERECALIBRATOR_SPARK_16c {
    container "ghcr.io/martinluttap/gatk:4.2.4.1"
    containerOptions '--cpus=16'

    input:
        path input
        path index
        path known_sites
        path known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
		
    output:
        path "${input.baseName}_bqsr.grp"	, emit: output_grp
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar BaseRecalibratorSpark --output ${input.baseName}_bqsr.grp --input ${input} --known-sites ${known_sites} --reference ${ref_fa}
        """
}

process GATK4_BASERECALIBRATOR_SPARK_8c {
    container "ghcr.io/martinluttap/gatk:4.2.4.1"
    containerOptions '--cpus=8'

    input:
        path input
        // path index
        path known_sites
        path known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
		
    output:
        path "${input.baseName}_bqsr.grp"	, emit: output_grp
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar BaseRecalibratorSpark --spark-master local[*]--output ${input.baseName}_bqsr.grp --input ${input} --known-sites ${known_sites} --reference ${ref_fa}
        """
}

process GATK4_BASERECALIBRATOR_SPARK_4c {
    container "ghcr.io/martinluttap/gatk:4.2.4.1"
    containerOptions '--cpus=4'

    input:
        path input
        path index
        path known_sites
        path known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
		
    output:
        path "${input.baseName}_bqsr.grp"	, emit: output_grp
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar BaseRecalibratorSpark --output ${input.baseName}_bqsr.grp --input ${input} --known-sites ${known_sites} --reference ${ref_fa}
        """
}

process GATK4_BASERECALIBRATOR {
    container "ghcr.io/martinluttap/gatk:4.2.4.1"

    input:
        path input
        path known_sites
        path known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
		
    output:
        path "${input.baseName}_bqsr.grp"	, emit: output_grp
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar BaseRecalibrator --output ${input.baseName}_bqsr.grp --input ${input} --known-sites ${known_sites} --reference ${ref_fa}
        """
}

workflow {
    GATK4_BASERECALIBRATOR(
        bam, ref_known_sites, ref_known_sites_tbi, ref_fa, ref_amb, ref_ann, ref_bwt, ref_fai, ref_pac, ref_sa, ref_dict
    )
    // GATK4_BASERECALIBRATOR_SPARK(
    //     bam, index, ref_known_sites, ref_known_sites_tbi, ref_fa, ref_amb, ref_ann, ref_bwt, ref_fai, ref_pac, ref_sa, ref_dict
    // )
    // GATK4_BASERECALIBRATOR_SPARK_16c(
    //     bam, index, ref_known_sites, ref_known_sites_tbi, ref_fa, ref_amb, ref_ann, ref_bwt, ref_fai, ref_pac, ref_sa, ref_dict
    // )
    // GATK4_BASERECALIBRATOR_SPARK_8c(
    //     bam, ref_known_sites, ref_known_sites_tbi, ref_fa, ref_amb, ref_ann, ref_bwt, ref_fai, ref_pac, ref_sa, ref_dict
    // )
    // GATK4_BASERECALIBRATOR_SPARK_4c(
    //     bam, index, ref_known_sites, ref_known_sites_tbi, ref_fa, ref_amb, ref_ann, ref_bwt, ref_fai, ref_pac, ref_sa, ref_dict
    // )
}