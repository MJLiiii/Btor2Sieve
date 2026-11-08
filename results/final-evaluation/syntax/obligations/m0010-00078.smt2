(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x2516 (bvsge i_4 (_ bv1 32))))
(not $x2516)))
(check-sat)
