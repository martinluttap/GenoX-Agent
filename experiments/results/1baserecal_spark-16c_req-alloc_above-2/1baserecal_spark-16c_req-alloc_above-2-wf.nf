import groovy.time.TimeCategory 
import groovy.time.TimeDuration

include { GATK4_BASERECAL as BASERECAL_DEF1 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/gatk_baserecal.nf"
include { GATK4_BASERECAL_SPARK_NO_LIMIT as BASERECAL_SPARK1 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/gatk_baserecal.nf"
include { GATK4_BASERECAL_SPARK_NO_LIMIT as BASERECAL_SPARK2 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/gatk_baserecal.nf"


Date loadStart = new Date()
println ("Data loading started ...")

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

BAM_PATH = "/home/cc/nextflow/read-files/bams/1500MB"
bam_file = Channel.fromPath(BAM_PATH + '/chr1to4.bam')

workflow {
    bam_file.view {
        "Input files: ${it}, num_files=${it.size()}"
    }.subscribe {
        Date loadEnd = new Date()

        TimeDuration td = TimeCategory.minus(loadEnd, loadStart)

        def logFile = new File("LoadDuration.txt")
        logFile.delete()
        logFile.append(td)
        println ("Loading done! Took " + td)
    }
    BASERECAL_SPARK1(
        bam_file, ref_known_sites, ref_known_sites_tbi, ref_fa, ref_amb, ref_ann, ref_bwt, ref_fai, ref_pac, ref_sa, ref_dict
    )
}