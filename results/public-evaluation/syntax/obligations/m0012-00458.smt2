(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x1428 (bvsge i_4 (_ bv0 3))))
(not $x1428)))
(check-sat)
