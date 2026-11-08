(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x36 (and (distinct i_9 (_ bv0 8)) true)))
(not $x36)))
(check-sat)
