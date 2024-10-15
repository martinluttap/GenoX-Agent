import groovy.time.TimeCategory 
import groovy.time.TimeDuration

include { FASTQC_NO_LIMIT as FASTQC1 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/fastqc.nf"
include { FASTQC_NO_LIMIT as FASTQC2 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/fastqc.nf"


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
READ_PATH = "/home/cc/nextflow/read-files/SRR24039108/SRR24039108_1.fastq.split"

Date loadStart = new Date()
println ("Data loading started ...")
fastq_files = Channel.fromPath(READ_PATH + '/SRR*_{1,2}.part_{001,002,003,004,005,006,007,008,009,010,011,012,013,014,015,016,017,018,019,020,021,022,023,024,025,026,027,028,029,030,031,032,033,034,035,036,037,038,039,040,041,042,043,044,045,046,047,048,049,050,051,055,053,054,055,056,057,058,059,060,061,062,063}.fastq').collect()
// fastq_files = Channel.fromPath(READ_PATH + '/SRR*_1.part_{001,002,003,004,005,006,007,008,009,010,011,012,013,014,015,016,017,018,019,020,021,022,023,024,025,026,027,028,029,030,031,032}.fastq').collect()
//                     .splitFastq(by: 1000000, limit:1000000, 
//                     pe:true, file: true)

// fastq_pair2 = Channel.fromFilePairs(READ_PATH + '/*_{1,2}.fastq')
            // .splitFastq(by: 250000, limit:250000, 
            // pe:true, file: true, compress: true)

workflow {
    fastq_files.view {
        "Paired FASTQ: ${it}, num_files=${it.size()}"
    }.subscribe {
        Date loadEnd = new Date()

        TimeDuration td = TimeCategory.minus(loadEnd, loadStart)

        def logFile = new File("LoadDuration.txt")
        logFile.delete()
        logFile.append(td)
        println ("Loading done! Took " + td)
    }
    FASTQC1(
        fastq_files
    )
    // FASTQC2(
    //     fastq_files
    // )
}