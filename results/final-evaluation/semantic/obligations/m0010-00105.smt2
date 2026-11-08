(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x78 (bvsle i_6 (_ bv255 8))))
(not $x78)))
(check-sat)
