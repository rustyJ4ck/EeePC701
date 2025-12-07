<?php

//
// 915gm/910gml memory timings parser
// https://github.com/rustyJ4ck/EeePC701
//
// 1) Enable mchbar -> CALL D:\bin\mchbar-enable.bat
// 2) RW allows only one instance, so close it before running this script 
// Usage: php mchbar_timings.php --with-read  # read timings from actual hardware registers using RW.exe
// Usage: php mchbar_timings.php --simple 0x110=0x88BC10D8 0x114=0x03508111 ... # or 114=03408110 to decode timings
//

// DDR2-400 CL3-3-3-9 defaults:
//  C0DRT0  Address: 0x110 	Value: 0x987820C8 
//  C0DRT1  Address: 0x114 	Value: 0x0290D211 
//  C0DRT2  Address: 0x118 	Value: 0x80000230 
//  C0DRC0  Address: 0x120 	Value: 0x40000A06 

class RegisterParser {

	private $mchbar = 0xFED14000;
	private $rwCmd  = 'D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command=';

	private $_readTimings = false; // --with-read
	private $_simplePrint = false; // --simple

    private $registers = [];
    public $spd = [];

	// cmd line overrides
    private $_regValues = [];

    public function addRegister($name, $address, $value, $bitFields) {
        $this->registers[+$address] = [
            'name' => $name,
            'address' => $address,
            'value' => $this->_readTimings ? $this->readAddr($address) : $value,
            'bitFields' => $bitFields
        ];
    }
    
    public function parseAndPrint() {
        foreach ($this->registers as $id => $register) {
        	if (isset($this->_regValues[$id]))
        		$register['value'] = $this->_regValues[$id];
            $this->printRegister($register);
            echo "\n";
        }
    }
   
    // Read reg. values from argv: 0x110=0x88BC10D8 or 110=88BC10D8   
    public function getRegValuesFromOpts($options) {
    	foreach ($options as $opt) {
    		if (preg_match('@(?P<reg>[\d]{3})=(?:0x)?(?P<value>[\dA-Z]+)@i', $opt, $match)) {
    			$regId = '0x'.$match['reg'];
    			$this->_regValues[+$regId] = '0x' . $match['value'];
    		}
    	}
    }

    private function printRegister($reg) {
        $value = hexdec($reg['value']);
        
        echo "=== {$reg['name']} === ";
        echo "Address: {$reg['address']} ";        
        echo "Value: {$reg['value']} ";
        echo chunk_split(str_pad(decbin($value), 32, '0', STR_PAD_LEFT), 4, ' ') . "\n";

        echo "\n";
        
        foreach ($reg['bitFields'] as $field) {
            $fieldValue = $this->extractBitField($value, $field['bits']);
            if ($this->_simplePrint)
            	printf("  %5s %-4s %s\n",  (@$field['id']?$field['id'].' ':''),
	            		(@$field['format'] ?  $field['format']($fieldValue) : $fieldValue),  
	            		$field['description']);
            else
            	printf("  Bits %-7s %-5s %-47s %10s | 0x%02X | %-6b %s\n", 
                        $field['bits'], 
                        (@$field['id']?$field['id'].' ':''),
                        $field['description'],
                        (@$field['format'] ?  $fieldValue . ')  ' . $field['format']($fieldValue) : $fieldValue),
                        $fieldValue,
                        $fieldValue,
                        (($range=@$field['range'])?$range[0].'..'.$range[1]:'')
						);
			 if (isset($field['id'])) $this->spd[$field['id']] = (@$field['format'] ? $field['format']($fieldValue) : $fieldValue);  
        }
    }
    
    private function extractBitField($value, $bitsSpec) {

 		$v=+$value;
 		$vb32=str_pad(decbin($v),32,'0',STR_PAD_LEFT);
 		if (strpos($bitsSpec, ':') !== false)
 			list($end,$beg)=explode(':',$bitsSpec);
 		else $end = $beg = $bitsSpec;	     		
 		$vb=substr($vb32,-1*$end-1,(1+$end-$beg));
 		return bindec($vb);

	    /*
        if (strpos($bitsSpec, ':') !== false) {
            // Range like "29:28"
            list($high, $low) = explode(':', $bitsSpec);
            $high = (int)$high;
            $low = (int)$low;
            $mask = ((1 << ($high - $low + 1)) - 1) << $low;
            return ($value & $mask) >> $low;
        } else {
            // Single bit like "17"
            $bit = (int)$bitsSpec;
            $mask = 1 << $bit;
            return ($value & $mask) ? 1 : 0;
        }
        */
    }

    function __construct($options) {
    	$this->_readTimings = false !== in_array('--with-read', $options);
		$this->_simplePrint = false !== in_array('--simple', $options);
		$this->getRegValuesFromOpts($options);

		// check options has reg values 0xN=0xNNNNNNNN
    }

    function readAddr($address) {
    	$cmd = $this->rwCmd . sprintf('"r32 0x%X"', $this->mchbar + +$address);
    	echo $cmd, PHP_EOL; 
    	$rwResult = explode('=', `$cmd`); 
    	$result = isset($rwResult[1]) ? trim($rwResult[1]) : false;
		return $result;
    }
}

function format_bool($v) { return $v ? 'Y' : 'N'; }

// Create parser instance
$parser = new RegisterParser($argv);

/*
Optimized:                                 1            2
 C0DRT0		00000110	FED14110	88BC20D8     88BC10D8
 C0DRT1		00000114	FED14114	03508111     03408110
 C0DRT2     00000118    FED14118	80000150     80000150
 C0DRC0		00000120	FED14120	40000906     40000906
*/

/*
Primary Timings (6-6-6-18)
1. CL = 6 cycles (CAS Latency)   		| 6 * 2.5 ns = 15 ns  | Delay between READ command and data availability 				 | Most critical for read performance	| 4-6 cycles for DDR2 @ 400MHz
2. tRCD = 6 cycles (RAS to CAS Delay)                         | Delay between activating a row (RAS) and reading/writing (CAS)   | Affects access latency to new rows
3. tRP = 6 cycles (Row Precharge)                             | Time to close one row before opening another                     | Affects bank switching performance
4. tRAS = 18 cycles (Active to Precharge) 18 * 2.5 ns = 45 ns | Minimum time a row must stay open                                | tRAS >= tRCD + tCL + tRTP  18 >= 6 + 6 + 6 = 18

Secondary Timings (24-51-3-6-3-3)
5. tRC = 24 cycles (Row Cycle Time)		| 24 * 2.5 ns = 60 ns |	Minimum time between successive ACTIVATE commands to same bank   | tRC = tRAS + tRP = 18 + 6 = 24 
6. tRFC = 51 cycles (Refresh Cycle Time)| 51 * 2.5 ns = 127.5 | Time required for refresh operations                             | Longer refresh cycles reduce performance during refresh
7. tRRD = 3 cycles (Row to Row Delay)   | 3 * 2.5 ns = 7.5 ns | Minimum time between ACTIVATE commands to different banks
8. tWR = 6 cycles (Write Recovery)							  | Delay between last write and precharge to same bank           	 | Ensures write data is properly stored
9. tWTR = 3 cycles (Write to Read Turnaround)                 | Internal delay from write to read command                        | Affects write-to-read switching performance
10. tRTP = 3 cycles (Read to Precharge)                       | Delay from read command to precharge                             | Affects read-to-precharge timing
*/

//  
$parser->addRegister("C0DRT0", "0x110", "0x987820C8", [
    ['bits' => '31:28', 'id' => 'WTP',  'description' => 'Write To Precharge Command Spacing (Same bank)', 	'range' => [5,13], 'min' => 'CL – 1 + BL/2 + WR'],    // reserved: 0000 – 0100 1110 – 1111
    ['bits' => '27:24', 'id' => 'WTR2', 'description' => 'Write To Read Command Spacing (Same rank)'	 , 	'range' => [4,11], 'min' => 'CL – 1 + BL/2 + WTR'],    // reserved: 0000 – 0011 1100 – 1111
    ['bits' => '23:22', 'id' => 'WRD',  'description' => 'Write-Read Command Spacing (Different Rank) ', 	'format' => function($v){return 6-$v;}, 'min' => 'BL/2 + TA –1'], // values: 00=6; 01=5; 10=4
    ['bits' => '21:20', 'id' => 'RTW',  'description' => 'Read-Write Command Spacing ',  				  	'format' => function($v){return 9-$v;}, 'min' => 'BL/2 + TA +1'], // 00=9; 01=8; 10=7; 11=6
    ['bits' => '19:18', 'id' => 'CCDw', 'description' => 'Write Command Spacing ',                         'format' => function($v){return 6-$v;}, 'min' => 'BL/2 + TA'], // 00=6; 01=5; 10=4 
    ['bits' => '16',    'id' => 'CCDr', 'description' => 'Read Command Spacing ',						  	'format' => function($v){return $v?5:6;}, 'range' => [5,6]], // 00=6; 01=5
    ['bits' => '15:11', 'id' => 'RD',   'description' => 'Read Delay',                                   	'range' => [3,31]], //2 is ok?
    ['bits' => '8:4',   'id' => 'WTP2', 'description' => 'Write Auto precharge to Activate (Same bank)', 	'range' => [4,19], 'min' => 'CL -1 + BL/2 + WR + RP'],         // Write Recovery Time		range: 100-10011
    ['bits' => '3:0',   'id' => 'RTP',  'description' => 'Read Auto precharge to Activate (Same bank)',		'min' =>  'RTPC + RP']          // Row Precharge Time   RTP + RP
]);

$parser->addRegister("C0DRT1", "0x114", "0x0290D211", [
    ['bits' => '29:28', 'id' => 'RTPC', 'description' => 'Read to Pre-charge BL/2', 	'format' => function($v){return [0=>4,1=>8][$v];}],
    ['bits' => '23:20', 'id' => 'RAS',  'description' => 'Active to Precharge Delay',		],
    ['bits' => '17',    'id' => 'RRD',	'description' => 'Activate to activate delay (clk)','format' => function($v){return [0=>2,1=>3][$v];}], // 0=2clk; 1=3clk
    ['bits' => '16',                    'description' => 'tRPALL Pre-All to Activate Delay'],
    ['bits' => '15:11', 'id' => 'RFC',  'description' => 'Refresh Cycle Time',				'range' => [3,31]	],
    ['bits' => '9:8',   'id' => 'CL',   'description' => 'CAS Latency ', 		            'format' => function($v){return [0=>5,1=>4,2=>3][$v];} ],
    ['bits' => '6:4',   'id' => 'RCD',  'description' => 'RAS to CAS Delay',				'format' => function($v){return 1+[0=>1,1=>2,2=>3,3=>4,4=>5][$v];}],
    ['bits' => '2:0',   'id' => 'RP',   'description' => 'Precharge to Activate Delay',		'format' => function($v){return 1+[0=>1,1=>2,2=>3,3=>4,4=>5][$v];}]

    //['bits' =>  false,  'id' => 'RC',  'description' => 'Activate to Activate Delay (same bank)',		'format' => function($v){return [0=>1,1=>2,2=>3,3=>4,4=>5][$v];}]
    //tRC = tRAS + tRP = 18 + 6 = 24 
]);

$parser->addRegister("C0DRT2", "0x118", "0x80000230", [
    ['bits' => '31:30', 'description' => 'CKE Deassert Duration', 'format' => function($v){return [0=>1,1=>'N/A',2=>3,3=>'N/A'][$v];}], // 01 = 3clk for DDR2
    ['bits' => '9:8',   'description' => 'Power Down Exit to CS# active time ','id' => 'XPDN', 'range' => [1,2], 'format' => function($v){return [0=>'N/A',1=>1,2=>2,3=>1][$v];}],   // 2clk for DDR2
    ['bits' => '7:5',   'description' => 'DRAM Page Close Idle Timer', 'format' => function($v){return [0=>'N/A',1=>8,2=>16,3=>'!res',7=>'Inf'][$v];}], // 001 = 8clk; 002 = 16?; 111 infinite; other reserved
    ['bits' => '4:0',   'description' => 'DRAM Power down Idle Timer', 'format' => function($v){return $v==31?'Inf':$v;}, 'range' => [8,16]] // 16 -> DDR2-400; 8 -> DDR2-533; 11111b = infinite CKE; other reserved 
]);

$parser->addRegister("C0DRC0", "0x120", "0x40000906", [
    ['bits' => '29',    'id' => 'IC', 	'description' => 'Initialization Complete', 'format' => 'format_bool'],
    ['bits' => '27:24', 				'description' => 'Active SDRAM Ranks'],
    ['bits' => '15',    				'description' => 'CMD copy enable (Single channel only)'],
    ['bits' => '10:8',  'id' => 'RMS', 	'description' => 'Refresh Mode Select (RMS)',  'format' => function($v){return [0=>'N',1=>'15.6',2=>'7.8'][$v];}],  // 00=disabled 01=15.6us 10=7.8
    ['bits' => '6:4',   'id' => 'SMD', 	'description' => 'Mode Select'],
    ['bits' => '2',     'id' => 'BL',  	'description' => 'Burst Length', 								'format' => function($v){return $v?8:4;}],  //0=4 1=8
    ['bits' => '1:0',   'id' => 'DT',  	'description' => 'DRAM Type']
]);

// Parse and display all registers
echo "EEEPC 701/900 DDR2 timings parser\n\n";

$parser->parseAndPrint();

$parser->spd['WTR'] = 2; // = 2 clock cycles for DDR2-400 regardless of CL

$parser->spd['WR'] = 3; // DDR-400 WR=3clk
$parser->spd['RC'] = $parser->spd['RAS'] + $parser->spd['RP'];

// Additional analysis for C0DRT1 timing values
/*
echo "=== C0DRT1 Timing Analysis ===\n";
$c0drt1 = hexdec("0x0390D111");
$tCL = ($c0drt1 >> 8) & 0x3;
$tRCD = ($c0drt1 >> 4) & 0x7;
$tRP = $c0drt1 & 0x7;
$tRAS = ($c0drt1 >> 20) & 0xF;

echo "CAS Latency (tCL): $tCL cycles\n";
echo "RAS to CAS Delay (tRCD): $tRCD cycles\n";  
echo "Row Precharge (tRP): $tRP cycles\n";
echo "Active to Precharge (tRAS): $tRAS cycles\n";
echo "Standard Timing: $tCL-$tRCD-$tRP-$tRAS\n";
*/
echo   "-------------------------------------------------------------------------------------\n";
printf("@ 200 MHz	%d-%d-%d-%-2d  (CL-RCD-RP-RAS) / %2d-%d-%d-%d-%d-%d  (RC-RFC-RRD-WR-WTR-RTP) \n\n", 
	$parser->spd['CL'],
	$parser->spd['RCD'],
	$parser->spd['RP'],
	$parser->spd['RAS'],
	// --
	$parser->spd['RC'],
	$parser->spd['RFC'],
	// --
	$parser->spd['RRD'],
	$parser->spd['WR'],
	$parser->spd['WTR'],
	$parser->spd['RTP']
);

?>
SPD Memory Timings	
HYMP125S64CP8-S6
@ 400 MHz	6-6-6-18  (CL-RCD-RP-RAS) / 24-51-3-6-3-3  (RC-RFC-RRD-WR-WTR-RTP)
@ 333 MHz	5-5-5-15  (CL-RCD-RP-RAS) / 20-43-3-5-3-3  (RC-RFC-RRD-WR-WTR-RTP)
@ 266 MHz	4-4-4-12  (CL-RCD-RP-RAS) / 16-34-2-4-2-2  (RC-RFC-RRD-WR-WTR-RTP)
HYMP125S64CP8-Y5                           
@ 200 MHz	3-3-3-9   (CL-RCD-RP-RAS) / 12-26-2-3-2-2  (RC-RFC-RRD-WR-WTR-RTP)
