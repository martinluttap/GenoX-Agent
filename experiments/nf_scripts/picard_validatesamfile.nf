import groovy.time.TimeCategory 
import groovy.time.TimeDuration

include { PICARD_VALIDATESAMFILE as PICARD_VALIDATESAMFILE } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/picard_validatesamfile.nf"


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
READ_PATH = "/home/cc/nextflow/read-files/bams/1500MB/"
bam_file = Channel.fromPath(READ_PATH + '/chr1to4.bam')
bai_file = Channel.fromPath(READ_PATH + '/chr1to4.bam.bai')
num_thread = 1

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
    PICARD_VALIDATESAMFILE(
        bam_file,
        bai_file
    )
}