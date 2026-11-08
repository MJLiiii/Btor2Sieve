(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x77 (bvsle i_8 (_ bv0 4))))
(not $x77)))
(check-sat)
