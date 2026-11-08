(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x1442 (bvsge i_4 (_ bv0 32))))
(not $x1442)))
(check-sat)
