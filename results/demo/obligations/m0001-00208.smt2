(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x150 (and (distinct i_9 (_ bv128 8)) true)))
(not $x150)))
(check-sat)
