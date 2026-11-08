(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x1042 (bvule i_4 (_ bv2147483647 32))))
(not $x1042)))
(check-sat)
